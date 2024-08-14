from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "coral_credits.api"

    def ready(self):
        from coral_credits.prom_exporter import CustomCollector
        from prometheus_client.core import REGISTRY

        REGISTRY.register(CustomCollector())
