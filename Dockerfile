FROM ubuntu:jammy as build-image

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends python3.10-venv git -y && \
    rm -rf /var/lib/apt/lists/*

# build into a venv we can copy across
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY ./requirements.txt /coral-credits/requirements.txt
RUN pip install -U pip setuptools
RUN pip install --requirement /coral-credits/requirements.txt

# Django fails to load templates if this is installed the "regular" way
# If we use an editable mode install then it works
COPY . /coral-credits
RUN pip install --no-deps -e /coral-credits

#
# Now the image we run with
#
FROM ubuntu:jammy as run-image

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends python3 tini ca-certificates -y && \
    rm -rf /var/lib/apt/lists/*

# Copy across the venv
COPY --from=build-image /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy across the app
COPY --from=build-image /coral-credits /coral-credits

# Create the user that will be used to run the app
ENV APP_UID 1001
ENV APP_GID 1001
ENV APP_USER app
ENV APP_GROUP app
RUN groupadd --gid $APP_GID $APP_GROUP && \
    useradd \
      --no-create-home \
      --no-user-group \
      --gid $APP_GID \
      --shell /sbin/nologin \
      --uid $APP_UID \
      $APP_USER

# Don't buffer stdout and stderr as it breaks realtime logging
ENV PYTHONUNBUFFERED 1

# Install application configuration using flexi-settings
ENV DJANGO_SETTINGS_MODULE flexi_settings.settings
ENV DJANGO_FLEXI_SETTINGS_ROOT /etc/coral-credits/settings.py
COPY ./etc/ /etc/
RUN mkdir -p /etc/coral-credits/settings.d

# Collect the static files
RUN /venv/bin/django-admin collectstatic

# By default, serve the app on port 8080 using the app user
EXPOSE 8080
USER $APP_UID
ENTRYPOINT ["tini", "-g", "--"]
CMD ["/venv/bin/gunicorn", "--config", "/etc/gunicorn/conf.py", "coral_credits.wsgi:application"]
