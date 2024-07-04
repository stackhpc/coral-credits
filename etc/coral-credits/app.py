"""
Application-specific settings.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/data/db.sqlite3",
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
