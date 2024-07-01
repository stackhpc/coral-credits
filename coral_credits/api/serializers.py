from rest_framework import serializers

from coral_credits.api import models


class ResourceClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["url", "name", "created"]


class ResourceProviderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProvider
        fields = ["url", "name", "created", "email", "info_url"]


class CreditAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CreditAccount
        fields = ["url", "name", "email", "created"]


class ResourceClass(serializers.ModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["name"]


class CreditAllocationResource(serializers.ModelSerializer):
    resource_class = ResourceClass()

    class Meta:
        model = models.CreditAllocationResource
        fields = ["resource_class", "resource_hours"]


class CreditAllocation(serializers.ModelSerializer):
    resources = CreditAllocationResource(many=True)

    class Meta:
        model = models.CreditAllocation
        fields = ["name", "start", "end", "resources"]


class ResourceConsumptionRecord(serializers.ModelSerializer):
    resource_class = ResourceClass()

    class Meta:
        model = models.ResourceConsumptionRecord
        fields = ["resource_class", "resource_hours"]


class Consumer(serializers.ModelSerializer):
    resource_provider = ResourceProviderSerializer()
    resources = ResourceConsumptionRecord(many=True)

    class Meta:
        model = models.Consumer
        fields = ["consumer_ref", "resource_provider", "start", "end", "resources"]


class ConsumerRequest(serializers.Serializer):
    consumer_ref = serializers.CharField(max_length=200)
    resource_provider_id = serializers.IntegerField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
