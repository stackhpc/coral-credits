from django.contrib import admin
from rest_framework import serializers

from coral_credits.api import models
from django.contrib.auth.models import User


class ResourceClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ['url', 'name', 'created']


class ResourceProviderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProvider
        fields = ['url', 'name', 'created', 'email', 'info_url']


class CreditAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CreditAccount
        fields = ['url', 'name', 'email', 'created']


class ResourceClass(serializers.ModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["name"]


class CreditAllocation(serializers.ModelSerializer):
    class Meta:
        model = models.CreditAllocation
        fields = ["name", "start", "end"]


class CreditAllocationResource(serializers.ModelSerializer):
    allocation = CreditAllocation()
    resource_class = ResourceClass()

    class Meta:
        model = models.CreditAllocationResource
        fields = ['allocation', 'resource_class', 'resource_hours']


class Consumer(serializers.ModelSerializer):
    resource_provider = ResourceProviderSerializer()

    class Meta:
        model = models.Consumer
        fields = ['consume_ref', 'resource_provider', 'start', 'end']


class ResourceConsumptionRecord(serializers.ModelSerializer):
    consumer = Consumer()
    resource_class = ResourceClass()

    class Meta:
        model = models.ResourceConsumptionRecord
        fields = ['consumer', 'resource_class', 'resource_hours']
