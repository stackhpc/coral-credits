"""
Django test settings for coral_credits project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import logging
import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "drf_spectacular",
    "rest_framework",
    "auditlog",
    "coral_credits.api",
]

AUDITLOG_INCLUDE_ALL_MODELS = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

ROOT_URLCONF = "coral_credits.urls"

SPECTACULAR_SETTINGS = {
    "TITLE": "Coral Credits API",
    "DESCRIPTION": 'Coral credits is a resource management system that helps build a \
        "coral reef style" fixed capacity cloud, cooperatively sharing community \
        resources through interfaces such as: Azimuth, OpenStack Blazar and Slurm.',
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # OTHER SETTINGS
}

WSGI_APPLICATION = "coral_credits.wsgi.application"

# By default, don't run in DEBUG mode
DEBUG = False

# In a Docker container, ALLOWED_HOSTS is always '*' - let the proxy worry about hosts
ALLOWED_HOSTS = ["*"]

# Make sure Django interprets the script name correctly if set
if "SCRIPT_NAME" in os.environ:
    FORCE_SCRIPT_NAME = os.environ["SCRIPT_NAME"]

# Set a default random secret key
# This can be overridden by files included later if desired
SECRET_KEY = get_random_secret_key()

# All logging should go to stdout/stderr to be collected

LOG_FORMAT = (
    "[%(levelname)s] [%(asctime)s] [%(name)s:%(lineno)s] [%(threadName)s] %(message)s"
)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
        },
    },
    "filters": {
        # Logging filter that only accepts records with a level < WARNING
        # This allows us to log level >= WARNING to stderr and level < WARNING to stdout
        "less_than_warning": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: record.levelno < logging.WARNING,
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
            "filters": ["less_than_warning"],
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "default",
            "level": "WARNING",
        },
    },
    "loggers": {
        "": {
            "handlers": ["stdout", "stderr"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propogate": True,
        },
    },
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
