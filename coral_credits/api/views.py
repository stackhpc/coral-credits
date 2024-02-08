from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from coral_credits.api import models
from coral_credits.api import serializers


class ResourceClassViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceClass.objects.all()
    serializer_class = serializers.ResourceClassSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceProviderViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceProvider.objects.all()
    serializer_class = serializers.ResourceProviderSerializer
    permission_classes = [permissions.IsAuthenticated]


class AccountViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = models.CreditAccount.objects.all()
        serializer = serializers.CreditAccountSerializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = models.CreditAccount.objects.all()
        account = get_object_or_404(queryset, pk=pk)
        serializer = serializers.CreditAccountSerializer(
            account, context={'request': request})
        account_summary = serializer.data

        # TODO(johngarbutt) look for any during the above allocations
        allocations_query = models.CreditAllocationResource.objects.filter(
            allocation__account__pk=pk
        )
        allocations = serializers.CreditAllocationResource(
            allocations_query, many=True
        )

        # TODO(johngarbutt) look for any during the above allocations
        consumers_query = models.ResourceConsumptionRecord.objects.filter(
            consumer__account__pk=pk
        )
        consumers = serializers.ResourceConsumptionRecord(
            consumers_query, many=True, context={'request': request}
        )

        account_summary["allocations"] = allocations.data
        account_summary["consumers"] = consumers.data

        # add resource_hours_remaining... must be a better way!
        for allocation in account_summary["allocations"]:
            allocation["resource_hours_remaining"] = float(allocation["resource_hours"])
            # if allocation
            for consumer in account_summary["consumers"]:
                consume_resource = consumer["resource_class"]["name"]
                if (allocation["resource_class"]["name"] == consume_resource):
                    allocation["resource_hours_remaining"] -= float(consumer["resource_hours"])
            consumers = account_summary["consumers"]

        return Response(account_summary)
