import os

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "coral_credits.api"

    def ready(self):
        if os.environ.get("REGISTER_PROM_COLLECTOR") == "true":
            return
        else:
            from coral_credits.prom_exporter import CustomCollector
            from prometheus_client.core import REGISTRY

            REGISTRY.register(CustomCollector())
            os.environ["REGISTER_PROM_COLLECTOR"] == "true"
