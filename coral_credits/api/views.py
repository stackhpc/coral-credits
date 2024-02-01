from rest_framework import permissions, viewsets

from coral_credits.api import models
from coral_credits.api import serializers

class ResourceClassViewSet(viewsets.ViewSet):
    queryset = models.ResourceClass.objects.all()
    serializer_class = serializers.ResourceClassSerializer
    permission_classes = [permissions.IsAuthenticated]

class AllocationViewSet(viewsets.ViewSet):
    queryset = models.Allocation.objects.all()
    serializer_class = serializers.AllocationSerializer
    permission_classes = [permissions.IsAuthenticated]