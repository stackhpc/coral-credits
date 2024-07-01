from django.db import models

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


class CreditAllocation(models.Model):
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
        return f"{self.account} from {self.start}"


class CreditAllocationResource(models.Model):
    allocation = models.ForeignKey(
        CreditAllocation, on_delete=models.CASCADE, related_name="resources"
    )
    resource_class = models.ForeignKey(
        ResourceClass, on_delete=models.DO_NOTHING, related_name="+"
    )
    resource_hours = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "allocation",
            "resource_class",
        )
        ordering = ("allocation__start",)

    def __str__(self) -> str:
        return f"{self.resource_class} for {self.allocation}"


class Consumer(models.Model):
    consumer_ref = models.CharField(max_length=200)
    resource_provider = models.ForeignKey(ResourceProvider, on_delete=models.DO_NOTHING)
    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(CreditAccount, on_delete=models.DO_NOTHING)
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        unique_together = (
            "consumer_ref",
            "resource_provider",
        )

    def __str__(self) -> str:
        return f"{self.consumer_ref}@{self.resource_provider}"


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
        return f"{self.consumer} from {self.resource_class}"
