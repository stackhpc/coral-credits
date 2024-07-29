# Default settings for gunicorn
# Also allows for overriding with environment variables
import os

# Configure the bind address
_host = os.environ.get("GUNICORN_HOST", "0.0.0.0")
_port = os.environ.get("GUNICORN_PORT", "8080")
bind = os.environ.get("GUNICORN_BIND", "{}:{}".format(_host, _port))

# TODO(tylerchristie): configure workers and threads?

# TODO(tylerchristie): configure logging
