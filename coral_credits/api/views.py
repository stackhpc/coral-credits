from django.db import transaction
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
        """
        List all Credit Accounts
        """
        queryset = models.CreditAccount.objects.all()
        serializer = serializers.CreditAccountSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Retreives a Credit Account Summary
        """
        queryset = models.CreditAccount.objects.all()
        account = get_object_or_404(queryset, pk=pk)
        serializer = serializers.CreditAccountSerializer(
            account, context={"request": request}
        )
        account_summary = serializer.data

        # TODO(johngarbutt) look for any during the above allocations
        all_allocations_query = models.CreditAllocation.objects.filter(account__pk=pk)
        allocations = serializers.CreditAllocation(all_allocations_query, many=True)

        # TODO(johngarbutt) look for any during the above allocations
        consumers_query = models.Consumer.objects.filter(account__pk=pk)
        consumers = serializers.Consumer(
            consumers_query, many=True, context={"request": request}
        )

        account_summary["allocations"] = allocations.data
        account_summary["consumers"] = consumers.data

        # add resource_hours_remaining... must be a better way!
        # TODO(johngarbut) we don't check the dates line up!!
        for allocation in account_summary["allocations"]:
            for resource_allocation in allocation["resources"]:
                if "resource_hours_remaining" not in resource_allocation:
                    resource_allocation["resource_hours_remaining"] = (
                        resource_allocation["resource_hours"]
                    )
                for consumer in account_summary["consumers"]:
                    for resource_consumer in consumer["resources"]:
                        consume_resource = resource_consumer["resource_class"]["name"]
                        if (
                            resource_allocation["resource_class"]["name"]
                            == consume_resource
                        ):
                            resource_allocation["resource_hours_remaining"] -= float(
                                resource_consumer["resource_hours"]
                            )

        return Response(account_summary)

    def update(self, request, pk=None):
        """
        Add a resource request

        Example request::
            {
                "consumer_ref": "vm_test42",
                "resource_provider_id": 1,
                "start": "2024-02-07T18:23:38Z",
                "end": "2024-02-08T18:22:44Z",
                "resources": [
                    {
                        "resource_class": {
                            "name": "CPU"
                        },
                        # TODO(tylerchristie): This should just be total amount of resource requested in reservation.
                        "resource_hours": 2.0
                    }
                ]
            }
        """
        resource_request = serializers.ConsumerRequest(data=request.data)
        resource_request.is_valid(raise_exception=True)

        rp_queryset = models.ResourceProvider.objects.all()
        resource_provider = get_object_or_404(
            rp_queryset, pk=request.data["resource_provider_id"]
        )

        account_queryset = models.CreditAccount.objects.all()
        account = get_object_or_404(account_queryset, pk=pk)

        resource_records = []
        for resource in request.data["resources"]:
            name = resource["resource_class"]["name"]
            resource_class = models.ResourceClass.objects.get(name=name)
            resource_records.append(
                dict(
                    resource_class=resource_class,
                    resource_hours=resource["resource_hours"],
                )
            )

        # TODO(johngarbutt): add validation we have enough credits

        with transaction.atomic():
            consumer = models.Consumer.objects.create(
                consumer_ref=request.data["consumer_ref"],
                account=account,
                resource_provider=resource_provider,
                start=request.data["start"],
                end=request.data["end"],
            )
            for resource_rec in resource_records:
                models.ResourceConsumptionRecord.objects.create(
                    consumer=consumer,
                    resource_class=resource_rec["resource_class"],
                    resource_hours=resource_rec["resource_hours"],
                )

        return self.retrieve(request, pk)
