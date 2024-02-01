from django.db import models

class ResourceClass(models.Model):
    name = models.CharField(max_length=200)

class ResourceProvider(models.Model):
    uuid = models.UUIDField()
    name = models.CharField(max_length=200)

class Account(models.Model):
    uuid = models.UUIDField()
    name = models.CharField(max_length=200)
    contact_email = models.EmailField()

class Allocation(models.Model):
    uuid = models.UUIDField()
    name = models.CharField(max_length=200)
    account = models.ForeignKey(Account, on_delete=models.DO_NOTHING)
    # TODO implement resource provider limits?
    start = models.DateTimeField()
    end = models.DateTimeField()

class AllocationResource(models.Model):
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    resource_class = models.ForeignKey(ResourceClass, on_delete=models.DO_NOTHING)
    resource_hours = models.DecimalField()

class Consumer(models.Model):
    uuid = models.UUIDField()
    models.CharField(max_length=200)
    account = models.ForeignKey(Account, on_delete=models.DO_NOTHING)
    resource_provider = models.ForeignKey(ResourceProvider, on_delete=models.DO_NOTHING)
    start = models.DateTimeField()
    end = models.DateTimeField()

class ResourceConsumptionRecord(models.Model):
    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE)
    resource_class = models.ForeignKey(ResourceClass, on_delete=models.DO_NOTHING)
    resource_hours = models.DecimalField()
