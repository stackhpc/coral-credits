from rest_framework import serializers

from coral_credits.api import models


class ResourceClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ['name']


class ResourceProviderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProvider
        fields = ['name', 'uuid']


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Account


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        models = models.Allocation


class ConsumerSerializer(serializers.ModelSerializer):
    class Meta:
        models = models.Consumer