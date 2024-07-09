from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions, viewsets, status
from rest_framework.response import Response

from coral_credits.api import models, serializers


class ResourceClassViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceClass.objects.all()
    serializer_class = serializers.ResourceClassSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceProviderViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceProvider.objects.all()
    serializer_class = serializers.ResourceProviderSerializer
    permission_classes = [permissions.IsAuthenticated]


class AccountViewSet(viewsets.ViewSet):
    queryset = models.CreditAccount.objects.all()
    serializer_class = serializers.CreditAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Retreives a Credit Account Summary"""
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
                            == consume_resource  # noqa: W503
                        ):
                            resource_allocation["resource_hours_remaining"] -= float(
                                resource_consumer["resource_hours"]
                            )

        return Response(account_summary)

class ConsumerViewSet(viewsets.ModelViewSet):
    queryset = models.Consumer.objects.all()
    serializer_class = serializers.ConsumerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        return self._create_or_update(request)

    def update(self, request):
        return self._create_or_update(request, current_lease_required=True)
    
    def check_create(self,request):
        return self._create_or_update(request, dry_run=True)
    
    def check_update(self,request):
        return self._create_or_update(request, current_lease_required=True, dry_run=True)
    
    @transaction.atomic
    def _create_or_update(self, request, current_lease_required=False, dry_run=False):
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
                # TODO(assumptionsandg): "lease_name": "my_new_lease"
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
                        # Resource request can be arbitrary, e.g.:
                        "inventories": {
                            "DISK_GB": {
                                "allocation_ratio": 1.0,
                                "max_unit": 35,
                                "min_unit": 1,
                                "reserved": 0,
                                "step_size": 1,
                                "total": 35
                            },
                            "MEMORY_MB": {
                                "allocation_ratio": 1.5,
                                "max_unit": 5825,
                                "min_unit": 1,
                                "reserved": 512,
                                "step_size": 1,
                                "total": 5825
                            },
                            "VCPU": {
                                "allocation_ratio": 16.0,
                                "max_unit": 4,
                                "min_unit": 1,
                                "reserved": 0,
                                "step_size": 1,
                                "total": 4
                            }
                        },
                        "resource_provider_generation": 7
                    }
                }
                ]
            },
            "current_lease" : 
                {
                    # Same as above, only exists if this is an update request
                }
        }
        """
        # Check request is valid
        resource_request = serializers.ConsumerRequest(
            data=request.data, current_lease_required=current_lease_required
        )
        resource_request.is_valid(raise_exception=True)

        context = resource_request.validated_data["context"]
        lease = resource_request.validated_data["lease"]
        if current_lease_required:
            current_lease = resource_request.validated_data["current_lease"]
            # If the request says it already has a lease, we look it up
            # We don't trust the request that the lease exists
            try:
                current_consumer = get_object_or_404(models.Consumer, consumer_uuid=current_lease.get('lease_id'))
                current_resource_requests = (
                    models.CreditAllocationResource.objects.filter(
                        consumer=current_consumer,
                    )
                )
                current_lease_start = timezone.make_aware(current_consumer.start)
                current_lease_end = timezone.make_aware(current_consumer.end)
                current_lease_duration = (current_lease_end - current_lease_start).total_seconds() / 3600  # Convert to hours

            except models.Consumer.DoesNotExist:
                return Response(
                    {"error": "No matching record found for current lease"},
                    status=status.HTTP_403_FORBIDDEN
                )
            

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
            
            # Amount is a dict with an arbitrary format:
            # for now we will just look for 'total'
            try:
                requested_resource_hours = (
                    float(amount['total']) * lease["reservations"]["min"] * lease_duration
                )
            except:
                return Response(
                            {
                                "error": f"Unable to recognise {resource_type} format {amount}"
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
            # Update scenario
            if current_lease_duration:
                # Case: user requests the same resource
                current_resource_request = current_resource_requests.filter(resource_class=resource_class).first()
                if current_resource_request:
                    current_resource_hours = current_resource_request.resource_hours
                    delta_resource_hours = requested_resource_hours - current_resource_hours
                # Case: user requests a new resource
                else:
                    delta_resource_hours = requested_resource_hours
            # Create scenario
            else:  
                delta_resource_hours = requested_resource_hours

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
                        <= delta_resource_hours
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
        # Don't modify the database on a dry_run
        if not dry_run:
            # Account has sufficient credits at time of database query, so we allocate resources
            # Update scenario
            if current_consumer:
                # We have CASCADE behaviour for ResourceConsumptionRecords
                # Also we roll back all db transactions if the final check fails
                current_consumer.delete()

            consumer = models.Consumer.objects.create(
                consumer_ref=lease.get("lease_name"),
                consumer_uuid=lease.get("lease_id"),
                resource_provider_account=resource_provider_account,
                user_ref=context["user_id"],
                start=lease_start,
                end=lease_end,
            )

            for resource_type, amount in lease["reservations"]["resource_requests"].items():
                    # TODO(tylerchristie) remove code duplication?
                    resource_class = models.ResourceClass.objects.get(name=resource_type)
                    resource_hours = float(amount) * lease["reservations"]["min"] * lease_duration

                    models.ResourceConsumptionRecord.objects.create(
                        consumer=consumer,
                        resource_class=resource_class,
                        resource_hours=resource_hours,
                    )

                    # Subtract expenditure from CreditAllocationResource
                    credit_allocation_resource = models.CreditAllocationResource.objects.filter(
                    allocation=credit_allocation,
                    resource_class = resource_class).update(resource_hours=F('resource_hours') - resource_hours)

            # Final check
            # TODO(tylerchristie): is select_for_update better than optimistic concurrency?
            # https://docs.djangoproject.com/en/5.0/ref/models/querysets/#select-for-update
            # it can block reads
            #
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
                {"message": "Consumer and resources requested successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        return Response(
                {"message": "Account has sufficient resources to fufill request"},
                status=status.HTTP_204_NO_CONTENT,
            )
