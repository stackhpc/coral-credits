from auditlog import models as auditlog_models
from django.contrib import admin

from coral_credits.api import models

# Register your models here.
admin.site.register(models.CreditAccount)
admin.site.register(models.CreditAllocation)
admin.site.register(models.CreditAllocationResource)
admin.site.register(models.Consumer)
admin.site.register(models.ResourceClass)
admin.site.register(models.ResourceConsumptionRecord)
admin.site.register(models.ResourceProvider)
