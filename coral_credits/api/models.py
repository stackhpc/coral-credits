from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

# from django.db.models import Q

# TODO(tylerchristie): add allocation window in here, to simplify.


class ResourceClass(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name}"


class ResourceProvider(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    email = models.EmailField()
    info_url = models.URLField()

    def __str__(self) -> str:
        return f"{self.name}"


class CreditAccount(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    email = models.EmailField()

    def __str__(self) -> str:
        return f"{self.name}"


class ResourceProviderAccount(models.Model):
    account = models.ForeignKey(CreditAccount, on_delete=models.CASCADE)
    provider = models.ForeignKey(ResourceProvider, on_delete=models.CASCADE)
    project_id = models.UUIDField()

    class Meta:
        unique_together = (
            (
                "account",
                "provider",
            ),
            ("provider", "project_id"),
        )

    def __str__(self) -> str:
        return (
            f"Project ID:{self.project_id} for Account:{self.account} "
            f"in Provider:{self.provider}"
        )


class CreditAllocation(models.Model):
    # TODO(tylerchristie): do we need a name here?
    name = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(CreditAccount, on_delete=models.DO_NOTHING)
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        unique_together = (
            (
                "name",
                "account",
            ),
            ("account", "start"),
        )

    def __str__(self) -> str:
        return f"{self.account} - {self.start}"


class CreditAllocationResource(models.Model):
    allocation = models.ForeignKey(
        CreditAllocation, on_delete=models.CASCADE, related_name="resources"
    )
    resource_class = models.ForeignKey(
        ResourceClass, on_delete=models.DO_NOTHING, related_name="+"
    )
    resource_hours = models.FloatField()
    original_resource_hours = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "allocation",
            "resource_class",
        )
        ordering = ("allocation__start",)

    def __str__(self) -> str:
        return (
            f"{self.resource_hours} hours allocated for {self.resource_class} "
            f"from {self.allocation}"
        )


@receiver(pre_save, sender=CreditAllocationResource)
def set_original_hours(sender, instance, **kwargs):
    if instance.pk is None:  # Only on creation
        instance.original_resource_hours = instance.resource_hours


class Consumer(models.Model):
    consumer_ref = models.CharField(max_length=200)
    consumer_uuid = models.UUIDField()
    resource_provider_account = models.ForeignKey(
        ResourceProviderAccount, on_delete=models.DO_NOTHING
    )
    user_ref = models.UUIDField()
    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        # TODO(tylerchristie): allow either/or nullable?
        # constraints = [
        #     models.CheckConstraint(
        #         check=Q(consumer_ref=False) | Q(consumer_uuid=False),
        #         name='not_both_null'
        #     )
        # ]
        unique_together = (
            "consumer_uuid",
            "resource_provider_account",
        )

    def __str__(self) -> str:
        return (
            f"consumer ref:{self.consumer_ref} with "
            f"id:{self.consumer_uuid}@{self.resource_provider_account}"
        )


class ResourceConsumptionRecord(models.Model):
    consumer = models.ForeignKey(
        Consumer, on_delete=models.CASCADE, related_name="resources"
    )
    resource_class = models.ForeignKey(
        ResourceClass, on_delete=models.DO_NOTHING, related_name="+"
    )
    resource_hours = models.FloatField()

    class Meta:
        unique_together = (
            "consumer",
            "resource_class",
        )
        ordering = ("consumer__start",)

    def __str__(self) -> str:
        return f"{self.resource_class}:{self.resource_hours} hours for {self.consumer}"
