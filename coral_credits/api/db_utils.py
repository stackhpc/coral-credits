from datetime import datetime
import logging
import uuid

from django.conf import settings
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import make_aware

from coral_credits.api import db_exceptions, models
from coral_credits.api.quota import QuotaPeriod

LOG = logging.getLogger(__name__)


def get_current_lease(current_lease_required, context, current_lease):
    if current_lease_required:
        current_consumer = get_object_or_404(
            models.Consumer, consumer_uuid=current_lease.id
        )
        current_resource_requests = models.ResourceConsumptionRecord.objects.filter(
            consumer=current_consumer
        )
        LOG.info(
            f"User {context.user_id} requested an update to lease "
            f"{current_lease.id}."
        )
        LOG.info(f"Current lease resource requests: {current_resource_requests}")

    else:
        current_consumer = None
        current_resource_requests = None

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
            if rcr.resource_class in resources:
                resources[rcr.resource_class] += rcr.resource_hours
            else:
                resources[rcr.resource_class] = rcr.resource_hours
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

    if not credit_allocations.exists():
        raise models.CreditAllocation.DoesNotExist

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
            LOG.info(
                f"for {resource_class} - current: {current_resource_requests}, "
                f"new: {requested_resource_hours}"
            )
            if (not current_resource_requests) and requested_resource_hours <= 0:
                raise db_exceptions.ResourceRequestFormatError(
                    f"Invalid request: {requested_resource_hours} hours requested for "
                    f"{resource_class}."
                )
            if current_resource_requests:
                delta_resource_hours = calculate_delta_resource_hours(
                    requested_resource_hours,
                    current_resource_requests,
                    resource_class,
                )
            else:
                delta_resource_hours = requested_resource_hours

            LOG.info(
                f"Calculated {delta_resource_hours} hours for lease {lease.id} with "
                f"requests {{resource_class: {resource_class}, amount: {amount}, "
                f"duration: {lease.duration}}}"
            )

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
        return requested_resource_hours - current_resource_request.resource_hours
    # Case: user requests a new resource
    return requested_resource_hours


def calculate_overlap_hours(
    record_start, record_end, period_start, period_end, total_hours: float
) -> float:
    """Calculate the prorated hours for a record that overlaps with a period."""
    # Convert dates to datetime for comparison
    period_start_dt = make_aware(datetime.combine(period_start, datetime.min.time()))
    period_end_dt = make_aware(datetime.combine(period_end, datetime.max.time()))

    # Find the overlap
    overlap_start = max(record_start, period_start_dt)
    overlap_end = min(record_end, period_end_dt)

    # Calculate the proportion of the record that falls within the period
    record_duration = (record_end - record_start).total_seconds()
    overlap_duration = (overlap_end - overlap_start).total_seconds()
    overlap_proportion = overlap_duration / record_duration
    LOG.info(
        f"{overlap_proportion*100:.2f}% of {total_hours} included in quota period."
    )
    return overlap_proportion * total_hours


def check_quota(resource_provider_account, resource_requests, allocation_hours):
    """Checks if resource requests would exceed quota limits for the period.

    Only enforces quota on the ResourceProviderAccount, not the CreditAccount.

    Returns True if the request is valid, raises exception otherwise.

    Args:
        resource_requests: Dictionary mapping ResourceClass to requested hours
        allocation_hours: Dictionary mapping ResourceClass to CreditAllocationResource

    Raises:
        QuotaExceeded: If the request would exceed quota limits
    """
    try:
        quota_enabled = settings.CORAL_CONFIG["QUOTA"]["ENABLED"]
    except Exception:
        quota_enabled = False
    if not quota_enabled:
        LOG.info("No quota rules set, skipping quota check.")
        return True

    period = QuotaPeriod.from_string(settings.CORAL_CONFIG["QUOTA"]["LIMIT_PERIOD"])
    usage_limit = (
        settings.CORAL_CONFIG["QUOTA"]["USAGE_LIMIT"] / 100
    )  # Convert percentage to decimal

    # Get period bounds
    start_date, end_date, period_days = period.get_bounds_and_days()

    LOG.info(
        f"Quota period is from {start_date} to {end_date}. Total days: {period_days}."
    )

    for resource_class, requested_hours in resource_requests.items():
        credit_allocation_resource = allocation_hours[resource_class]
        credit_allocation_duration = (
            credit_allocation_resource.allocation.end
            - credit_allocation_resource.allocation.start
        ).days + 1

        LOG.info(
            f"Initial credit allocation for {resource_class} : "
            f"{credit_allocation_resource.original_resource_hours} hours "
            f"over {credit_allocation_duration} days"
        )
        # Calculate daily average allowed from total allocation
        daily_avg = (
            credit_allocation_resource.original_resource_hours
            / credit_allocation_duration
        )

        LOG.info(
            f"daily average of {daily_avg} hours is calculated for {resource_class}."
        )
        # Calculate maximum allowed for this period
        period_max = daily_avg * period_days * usage_limit
        LOG.info(f"Quota allowance for the period is {period_max} hours.")

        # Get current usage in this period

        # Get all records that land within the period.
        consumption_records = models.ResourceConsumptionRecord.objects.filter(
            consumer__resource_provider_account=resource_provider_account,
            resource_class=resource_class,
            consumer__start__lte=end_date,
            consumer__end__gte=start_date,
        ).values("resource_hours", "consumer__start", "consumer__end")

        sum = next(iter(consumption_records.aggregate(Sum("resource_hours")).values()))
        LOG.info(f"Existing consumption during quota period: {sum}")
        # We need to discount any partial hours from records that land outside the quota
        # period. E.g. period is 10/10 to 17/10, but we have a record from 8/10 to 12/10
        # We only want to count the hours in 10/10 - 12/10, not 8/10 - 10/10.
        # Calculate prorated usage:
        current_usage = 0.0
        for record in consumption_records:
            prorated_hours = calculate_overlap_hours(
                record["consumer__start"],
                record["consumer__end"],
                start_date,
                end_date,
                record["resource_hours"],
            )
            current_usage += prorated_hours

        LOG.info(
            f"Resource Provider Account {resource_provider_account} has used "
            f"{current_usage:.2f} hours for resource class {resource_class} over "
            "the quota period."
        )

        # Check if new request would exceed quota
        if current_usage + requested_hours > period_max:
            raise db_exceptions.QuotaExceeded(
                f"Request would exceed {period.value} quota for {resource_class.name}. "
                f"Current usage: {current_usage:.2f} hours, "
                f"Requested: {requested_hours:.2f} hours, "
                f"Maximum allowed: {period_max:.2f} hours "
                f"(Daily avg: {daily_avg:.2f} × "
                f"Period days: {period_days} × "
                f"Usage limit: {usage_limit*100}%)"
            )
        LOG.info(
            f"Request would use an additional {requested_hours} hours of {period_max} "
            f"for a total of {((requested_hours + (sum or 0)) / period_max) * 100:.2f}%"
            " of quota limit."
        )
    return True


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
    lease,
    resource_provider_account,
    context,
    resource_requests,
    credit_allocations,
    current_consumer,
    current_resource_requests,
):
    # We use a temporary UUID to avoid integrity errors
    # Whilst we create the new ResourceConsumptionRecords.
    consumer = models.Consumer.objects.create(
        consumer_ref=lease.name,
        consumer_uuid=uuid.uuid4(),
        resource_provider_account=resource_provider_account,
        user_ref=context.user_id,
        start=lease.start_date,
        end=lease.end_date,
    )

    for resource_class in resource_requests:
        if current_resource_requests:
            current_resource_hours = (
                current_resource_requests.filter(resource_class=resource_class)
                .first()
                .resource_hours
            )
        else:
            current_resource_hours = 0

        models.ResourceConsumptionRecord.objects.create(
            consumer=consumer,
            resource_class=resource_class,
            resource_hours=current_resource_hours + resource_requests[resource_class],
        )
        # Subtract expenditure from CreditAllocationResource
        # Or add, if the update delta is < 0
        credit_allocations[resource_class].resource_hours = round(
            credit_allocations[resource_class].resource_hours
            - resource_requests[resource_class],
            0,
        )
        credit_allocations[resource_class].save()

    if current_consumer:
        # We have CASCADE behaviour for ResourceConsumptionRecords
        # Also we roll back all db transactions if the final check fails
        current_consumer.delete()
    # Now we set the real ID
    consumer.consumer_uuid = lease.id
    consumer.save()


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
