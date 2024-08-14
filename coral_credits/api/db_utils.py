from django.shortcuts import get_object_or_404
from django.utils import timezone

from coral_credits.api import db_exceptions, models


def get_current_lease(current_lease):
    current_consumer = get_object_or_404(
        models.Consumer, consumer_uuid=current_lease.id
    )
    current_resource_requests = models.CreditAllocationResource.objects.filter(
        consumer=current_consumer,
    )
    return current_consumer, current_resource_requests


def get_resource_provider_account(project_id):
    resource_provider_account = models.ResourceProviderAccount.objects.get(
        project_id=project_id
    )
    return resource_provider_account


def get_all_resource_provider_account():
    resource_provider_accounts = models.ResourceProviderAccount.objects.all()
    return resource_provider_accounts


def get_all_active_reservations(resource_provider_account):
    """Get all active reservation resources for an account:

    Returns a list of dictionaries of the form:
    [
        {"resource_class": "resource_hours"},
        {"resource_class": "resource_hours"},
        ...
    ]
    """
    # TODO(tylerchristie): can probably refactor the credit check with this function.
    resources = {}
    consumers = models.Consumer.objects.filter(
        resource_provider_account=resource_provider_account
    )
    for c in consumers:
        resource_consumption_records = models.ResourceConsumptionRecord.objects.filter(
            consumer=c
        )
        for rcr in resource_consumption_records:
            resource_class = models.ResourceClass.objects.filter(
                id=rcr.resource_class
            ).first()
            if resource_class in resources:
                resources[resource_class] += rcr.resource_hours
            else:
                resources[resource_class] = rcr.resource_hours
    return resources


def get_credit_allocation(id):
    now = timezone.now()
    try:
        credit_allocation = models.CreditAllocation.objects.filter(
            id=id, start__lte=now, end__gte=now
        ).first()
    except models.CreditAllocation.DoesNotExist:
        raise db_exceptions.NoCreditAllocation("Invalid allocation_id")
    return credit_allocation


def get_all_credit_allocations(resource_provider_account):
    # Find all associated active CreditAllocations
    # Make sure we only look for CreditAllocations valid for the current time
    now = timezone.now()
    credit_allocations = models.CreditAllocation.objects.filter(
        account=resource_provider_account.account, start__lte=now, end__gte=now
    ).order_by("pk")

    return credit_allocations


def get_credit_allocation_resources(credit_allocations, resource_classes):
    """Returns a dictionary of the form:

    {
        "resource_class": "credit_resource_allocation"
    }
    """
    credit_allocation_resources = get_all_credit_allocation_resources(
        credit_allocations
    )
    for resource_class in resource_classes:
        if resource_class not in credit_allocation_resources:
            raise db_exceptions.NoCreditAllocation(
                f"No credit allocated for resource_type {resource_class}"
            )
    return credit_allocation_resources


def get_all_credit_allocation_resources(credit_allocations):
    """Returns a dictionary of the form:

    {
        "resource_class": "credit_resource_allocation"
    }
    """
    resource_allocations = {}
    for credit_allocation in credit_allocations:
        credit_allocation_resources = models.CreditAllocationResource.objects.filter(
            allocation=credit_allocation
        )
        # TODO(tylerchristie): I think this breaks for the case where we have
        # multiple credit allocations for the same resource_class.
        for car in credit_allocation_resources:
            resource_allocations[car.resource_class] = car

    return resource_allocations


def get_resource_class(resource_class_name):
    try:
        resource_class = models.ResourceClass.objects.get(name=resource_class_name)
    except models.ResourceClass.DoesNotExist:
        raise db_exceptions.NoResourceClass(
            f"Resource class '{resource_class_name}' does not exist."
        )
    return resource_class


def get_valid_allocations(resources):
    """Validates a dictionary of resource allocations.

    Returns a list of dictionaries of the form:

    [
        {"VCPU": "resource_hours"},
        {"MEMORY_MB": "resource_hours"},
        ...
    ]
    """
    try:
        allocations = {}
        for resource_class_name, resource_hours in resources.items():
            resource_class = get_resource_class(resource_class_name)
            allocations[resource_class] = float(resource_hours)
    except ValueError:
        raise db_exceptions.ResourceRequestFormatError(
            f"Invalid value for resource hours: '{resource_hours}'"
        )
    return allocations


def get_resource_requests(lease, current_resource_requests=None):
    """Returns a dictionary of the form:

    {
        "resource_class": "resource_hours"
    }
    """
    resource_requests = {}

    for (
        resource_type,
        amount,
    ) in lease.resource_requests.resources.items():
        resource_class = get_object_or_404(models.ResourceClass, name=resource_type)
        try:
            # Keep it simple, ust take min for now
            # TODO(tylerchristie): check we can allocate max
            # CreditAllocationResource is a record of the number of resource_hours
            # available for one unit of a ResourceClass, so we multiply
            # lease_duration by units required.
            requested_resource_hours = round(
                float(amount) * lease.duration,
                1,
            )
            if current_resource_requests:
                delta_resource_hours = calculate_delta_resource_hours(
                    requested_resource_hours,
                    current_resource_requests,
                    resource_class,
                )
            else:
                delta_resource_hours = requested_resource_hours

            resource_requests[resource_class] = delta_resource_hours

        except KeyError:
            raise db_exceptions.ResourceRequestFormatError(
                f"Unable to recognize {resource_type} format {amount}"
            )

    return resource_requests


def calculate_delta_resource_hours(
    requested_resource_hours, current_resource_requests, resource_class
):
    # Case: user requests the same resource
    current_resource_request = current_resource_requests.filter(
        resource_class=resource_class
    ).first()
    if current_resource_request:
        current_resource_hours = current_resource_request.resource_hours
        return requested_resource_hours - current_resource_hours
    # Case: user requests a new resource
    return requested_resource_hours


def check_credit_allocations(resource_requests, credit_allocations):
    """Subtracts resources requested from credit allocations.

    Fails if any result is negative.
    """

    result = {}
    for resource_class in credit_allocations:
        result[resource_class] = (
            credit_allocations[resource_class].resource_hours
            - resource_requests[resource_class]
        )

        if result[resource_class] < 0:
            raise db_exceptions.InsufficientCredits(
                f"Insufficient {resource_class.name} credits available. "
                f"Requested:{resource_requests[resource_class]}, "
                f"Available:{credit_allocations[resource_class]}"
            )

    return result


def check_credit_balance(credit_allocations, resource_requests):
    # TODO(tylerchristie) Fresh DB query
    credit_allocation_resources = get_credit_allocation_resources(
        credit_allocations, resource_requests.keys()
    )
    for allocation in credit_allocation_resources.values():

        if allocation.resource_hours < 0:
            # We raise an exception so the rollback is handled
            raise db_exceptions.InsufficientCredits(
                (
                    f"Insufficient "
                    f"{allocation.resource_class.name} "
                    f"credits after allocation."
                )
            )


def spend_credits(
    lease, resource_provider_account, context, resource_requests, credit_allocations
):

    consumer = models.Consumer.objects.create(
        consumer_ref=lease.name,
        consumer_uuid=lease.id,
        resource_provider_account=resource_provider_account,
        user_ref=context.user_id,
        start=lease.start_date,
        end=lease.end_date,
    )

    for resource_class in resource_requests:
        models.ResourceConsumptionRecord.objects.create(
            consumer=consumer,
            resource_class=resource_class,
            resource_hours=resource_requests[resource_class],
        )
        # Subtract expenditure from CreditAllocationResource
        credit_allocations[resource_class].resource_hours = (
            credit_allocations[resource_class].resource_hours
            - resource_requests[resource_class]
        )
        credit_allocations[resource_class].save()


def create_credit_resource_allocations(credit_allocation, resource_allocations):
    """Allocates resource credits to a given credit allocation.

    Returns a list of new/updated CreditAllocationResources:
    [
        CreditAllocationResource
    ]
    """
    cars = []
    for resource_class, resource_hours in resource_allocations.items():
        # TODO(tyler) logging create or update?
        car, created = models.CreditAllocationResource.objects.get_or_create(
            allocation=credit_allocation,
            resource_class=resource_class,
            defaults={"resource_hours": resource_hours},
        )
        # If exists, update:
        if not created:
            car.resource_hours += resource_hours
            car.save()

        # Refresh from db to get the updated resource_hours
        car.refresh_from_db()
        cars.append(car)
    return cars
