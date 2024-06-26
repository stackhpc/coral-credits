FROM ubuntu:jammy as build-image

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends python3.10-venv git -y && \
    rm -rf /var/lib/apt/lists/*

# build into a venv we can copy across
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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
COPY --from=build-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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

# TODO(tylerchristie): django flexi settings  

# By default, serve the app on port 8080 using the app user
EXPOSE 8080
USER $APP_UID
ENTRYPOINT ["tini", "-g", "--"]
#TODO(tylerchristie): use gunicorn + wsgi like azimuth
CMD ["python", "manage.py", "runserver", "0.0.0.0:8080"]