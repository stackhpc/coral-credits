import uuid

from django.db import transaction
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from coral_credits.api import db_exceptions, db_utils, models, serializers


class CreditAllocationViewSet(viewsets.ModelViewSet):
    queryset = models.CreditAllocation.objects.all()
    serializer_class = serializers.CreditAllocationSerializer
    # permission_classes = [permissions.IsAuthenticated]


class CreditAllocationResourceViewSet(viewsets.ModelViewSet):
    queryset = models.CreditAllocationResource.objects.all()
    serializer_class = serializers.CreditAllocationResourceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, allocation_pk=None):
        """Allocate credits to a dictionary of resource classes.

        Example Request:
        {
            "resources": {"VCPU": 50, "MEMORY_MB": 2000, "DISK_GB": 1000},
        }
        """

        resources = self._validate_request(request)

        try:
            allocation = db_utils.get_credit_allocation(allocation_pk)
            allocations = db_utils.get_valid_allocations(resources)
        except db_exceptions.NoCreditAllocation as e:
            # No Credit Allocation
            return _http_403_forbidden(repr(e))
        except db_exceptions.NoResourceClass as e:
            # Resource requested doesn't exist.
            return _http_403_forbidden(repr(e))
        except db_exceptions.ResourceRequestFormatError as e:
            # Invalid resource_hours format.
            return _http_403_forbidden(repr(e))

        # TODO(tylerchristie) any exceptions this could throw?
        updated_allocations = db_utils.create_credit_resource_allocations(
            allocation, allocations
        )
        serializer = serializers.CreditAllocationResourceSerializer(
            updated_allocations, many=True, context={"request": request}
        )
        return _http_200_ok(serializer.data)

    def _validate_request(self, request):

        resource_allocations = serializers.ResourceRequestSerializer(data=request.data)

        resource_allocations.is_valid(raise_exception=True)
        allocation_request = resource_allocations.create(
            resource_allocations.validated_data
        )
        return allocation_request.resources


class ResourceClassViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceClass.objects.all()
    serializer_class = serializers.ResourceClassSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceProviderViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceProvider.objects.all()
    serializer_class = serializers.ResourceProviderSerializer
    permission_classes = [permissions.IsAuthenticated]


class ResourceProviderAccountViewSet(viewsets.ModelViewSet):
    queryset = models.ResourceProviderAccount.objects.all()
    serializer_class = serializers.ResourceProviderAccountSerializer
    permission_classes = [permissions.IsAuthenticated]


class AccountViewSet(viewsets.ModelViewSet):
    queryset = models.CreditAccount.objects.all()
    serializer_class = serializers.CreditAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Retreives a Credit Account Summary"""
        # TODO(tylerchristie): refactor
        queryset = models.CreditAccount.objects.all()
        account = get_object_or_404(queryset, pk=pk)
        serializer = serializers.CreditAccountSerializer(
            account, context={"request": request}
        )
        account_summary = serializer.data

        # TODO(johngarbutt) look for any during the above allocations
        all_allocations_query = models.CreditAllocation.objects.filter(account__pk=pk)
        allocations = serializers.CreditAllocationSerializer(
            all_allocations_query, many=True
        )

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
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        return self._create_or_update(request)

    def update(self, request):
        return self._create_or_update(request, current_lease_required=True)

    def check_create(self, request):
        return self._create_or_update(request, dry_run=True)

    def check_update(self, request):
        return self._create_or_update(
            request, current_lease_required=True, dry_run=True
        )

    @transaction.atomic
    def _create_or_update(self, request, current_lease_required=False, dry_run=False):
        """Process a request for a reservation.

        see consumer_tests.py for example requests.
        """
        # TODO(tylerchristie): remove when blazar has commit hook.
        request.data["lease"]["id"] = uuid.uuid4()
        context, lease, current_lease = self._validate_request(
            request, current_lease_required
        )

        # Ignore other types of reservation for now.
        # TODO(tylerchristie): don't.
        if any([res.resource_type != "flavor:instance" for res in lease.reservations]):
            return _http_403_forbidden("Resource type is not supported.")

        if current_lease_required:
            try:
                current_consumer, current_resource_requests = (
                    db_utils.get_current_lease(current_lease)
                )
            except models.Consumer.DoesNotExist:
                return _http_403_forbidden("No matching record found for current lease")

        try:
            resource_provider_account = db_utils.get_resource_provider_account(
                context.project_id
            )
        except models.ResourceProviderAccount.DoesNotExist:
            return _http_403_forbidden("No matching ResourceProviderAccount found")

        credit_allocations = db_utils.get_all_credit_allocations(
            resource_provider_account
        )

        if not credit_allocations.exists():
            return _http_403_forbidden("No active CreditAllocation found")

        # Check resource credit availability (first check)
        try:
            if current_lease_required:
                resource_requests = db_utils.get_resource_requests(
                    lease, current_resource_requests
                )
            else:
                resource_requests = db_utils.get_resource_requests(lease)
            allocation_hours = db_utils.get_credit_allocation_resources(
                credit_allocations, resource_requests.keys()
            )
            db_utils.check_credit_allocations(resource_requests, allocation_hours)
        except db_exceptions.ResourceRequestFormatError as e:
            # Incorrect resource request format
            return _http_403_forbidden(repr(e))
        except db_exceptions.InsufficientCredits as e:
            # Insufficient credits
            return _http_403_forbidden(repr(e))
        except db_exceptions.NoCreditAllocation as e:
            # No credit for resource class
            return _http_403_forbidden(repr(e))

        # Don't modify the database on a dry_run
        if not dry_run:
            # Account has sufficient credits at time of database query,
            # so we allocate resources.
            # Update scenario:
            if current_lease_required:
                # We have CASCADE behaviour for ResourceConsumptionRecords
                # Also we roll back all db transactions if the final check fails
                current_consumer.delete()
            try:
                db_utils.spend_credits(
                    lease,
                    resource_provider_account,
                    context,
                    resource_requests,
                    allocation_hours,
                )
            except IntegrityError as e:
                # Lease ID is not unique
                # TODO(tylerchristie) does blazar give the same UUID for a lease update?
                return _http_403_forbidden(repr(e))

            # Final check
            db_utils.check_credit_balance(credit_allocations, resource_requests)
            return _http_204_no_content("Consumer and resources requested successfully")

        return _http_204_no_content(
            "Account has sufficient resources to fufill request"
        )

    def _validate_request(self, request, current_lease_required):
        resource_request = serializers.ConsumerRequestSerializer(
            data=request.data, current_lease_required=current_lease_required
        )
        resource_request.is_valid(raise_exception=True)
        consumer_request = resource_request.create(resource_request.validated_data)
        return (
            consumer_request.context,
            consumer_request.lease,
            consumer_request.current_lease,
        )


def _http_403_forbidden(msg):
    return Response(
        {"error": msg},
        status=status.HTTP_403_FORBIDDEN,
    )


def _http_204_no_content(msg):
    return Response(
        {"message": msg},
        status=status.HTTP_204_NO_CONTENT,
    )


def _http_200_ok(msg):
    return Response(
        {"data": msg},
        status=status.HTTP_200_OK,
    )
