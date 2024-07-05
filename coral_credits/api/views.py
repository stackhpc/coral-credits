from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions, viewsets, status
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

    @transaction.atomic
    def create(self, request, pk=None):
        """
        Process a request for a reservation.

        Example (blazar) request:
        {
            "context": {
                "user_id": "c631173e-dec0-4bb7-a0c3-f7711153c06c",
                "project_id": "a0b86a98-b0d3-43cb-948e-00689182efd4",
                "auth_url": "https://api.example.com:5000/v3",
                "region_name": "RegionOne"
            },
            "lease": {
                # TODO(assumptionsandg): "lease_id": "e96b5a17-ada0-4034-a5ea-34db024b8e04"
                # TODO(assumptionsandg): "lease_name": "e96b5a17-ada0-4034-a5ea-34db024b8e04"
                "start_date": "2020-05-13T00:00:00.012345+02:00",
                "end_time": "2020-05-14T23:59:00.012345+02:00",
                "reservations": [
                {
                    "resource_type": "physical:host",
                    "min": 2,
                    "max": 3,
                    "hypervisor_properties": "[]",
                    "resource_properties": "[\"==\", \"$availability_zone\", \"az1\"]",
                    "allocations": [
                    {
                        "id": "1",
                        "hypervisor_hostname": "32af5a7a-e7a3-4883-a643-828e3f63bf54",
                        "extra": {
                        "availability_zone": "az1"
                        }
                    },
                    {
                        "id": "2",
                        "hypervisor_hostname": "af69aabd-8386-4053-a6dd-1a983787bd7f",
                        "extra": {
                        "availability_zone": "az1"
                        }
                    }
                    ]
                    # TODO(assumptionsandg): "resource_requests" :
                    {
                        "vcpu" / "pcpu" : "8"
                        "memory" : "4096" # MB ?
                        "storage" : "30" # GB ?
                        "storage_type" : "SSD"
                    }
                }
                ]
            }
            }
        """
        # Check request is valid
        resource_request = serializers.ConsumerRequest(
            data=request.data, current_lease_required=False
        )
        resource_request.is_valid(raise_exception=True)

        context = resource_request.validated_data["context"]
        lease = resource_request.validated_data["lease"]

        # Match the project_id with a ResourceProviderAccount
        try:
            resource_provider_account = models.ResourceProviderAccount.objects.get(
                project_id=context["project_id"]
            )
        except models.ResourceProviderAccount.DoesNotExist:
            return Response(
                {"error": "No matching ResourceProviderAccount found"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Find all associated active CreditAllocations
        # Make sure we only look for CreditAllocations valid for the current time
        now = timezone.now()
        credit_allocations = models.CreditAllocation.objects.filter(
            account=resource_provider_account.account, start__lte=now, end__gte=now
        ).order_by("-start")

        if not credit_allocations.exists():
            return Response(
                {"error": "No active CreditAllocation found"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Calculate lease duration
        lease_start = timezone.make_aware(lease["start_date"])
        lease_end = timezone.make_aware(lease["end_time"])
        lease_duration = (
            lease_end - lease_start
        ).total_seconds() / 3600  # Convert to hours

        # Check resource credit availability (first check)
        for resource_type, amount in lease["reservations"]["resource_requests"].items():
            # Check resource type requested is valid
            resource_class = get_object_or_404(models.ResourceClass, name=resource_type)
            # Keep it simple, ust take min for now
            # TODO(tylerchristie): check we can allocate max
            # CreditAllocationResource is a record of the number of resource_hours available for
            # one unit of a ResourceClass, so we multiply lease_duration by units required.
            requested_resource_hours = (
                float(amount) * lease["reservations"]["min"] * lease_duration
            )

            for credit_allocation in credit_allocations:
                # We know we only get one result because (allocation,resource_class) together is unique
                credit_allocation_resource = (
                    models.CreditAllocationResource.objects.filter(
                        allocation=credit_allocation, resource_class=resource_class
                    ).first()
                )
                if credit_allocation_resource:
                    if (
                        credit_allocation_resource.resource_hours
                        < requested_resource_hours
                    ):
                        return Response(
                            {
                                "error": f"Insufficient {resource_type} credits available"
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
                else:
                    return Response(
                        {
                            "error": f"No credit allocated for resource_type {resource_type}"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        # Account has sufficient credits at time of database query, so we allocate resources
        # Create Consumer and ResourceConsumptionRecords
        consumer = models.Consumer.objects.create(
            consumer_ref=lease.get("lease_name"),
            consumer_uuid=lease.get("lease_id"),
            resource_provider_account=resource_provider_account,
            user_ref=context["user_id"],
            start=lease_start,
            end=lease_end,
        )

        for reservation in lease["reservations"]:
            for resource_type, amount in reservation["resource_type"].items():
                # TODO(tylerchristie) remove code duplication?
                resource_class = models.ResourceClass.objects.get(name=resource_type)
                resource_hours = float(amount) * reservation["min"] * lease_duration

                models.ResourceConsumptionRecord.objects.create(
                    consumer=consumer,
                    resource_class=resource_class,
                    resource_hours=resource_hours,
                )

        # Final check
        # TODO(tylerchristie): is select_for_update better than optimistic concurrency?
        # https://docs.djangoproject.com/en/5.0/ref/models/querysets/#select-for-update
        for (
            credit_allocation_resource
        ) in models.CreditAllocationResource.objects.filter(
            allocation=credit_allocation
        ):
            if credit_allocation_resource.resource_hours < 0:
                transaction.set_rollback(True)
                return Response(
                    {
                        "error": f"Insufficient {credit_allocation_resource.resource_class.name} credits after allocation"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        return Response(
            {"message": "Consumer and resources created successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )

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

            class ConsumerRequest(serializers.Serializer):
                consumer_ref = serializers.CharField(max_length=200)
                resource_provider_id = serializers.IntegerField()
                start = serializers.DateTimeField()
                end = serializers.DateTimeField()
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
