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
        # TOOD(johngarbutt) try add url back?
        fields = ['url', 'name', 'email', 'created']
