import json
import uuid

from django.urls import reverse
import pytest
from pytest_lazy_fixtures import lf as lazy_fixture
from rest_framework import status

import coral_credits.api.models as models

# TODO(tylerchristie): check and commit tests


def consumer_request(url, api_client, request_data, expected_response):
    response = api_client.post(
        url,
        data=json.dumps(request_data),
        content_type="application/json",
        secure=True,
    )

    assert response.status_code == expected_response, (
        f"Expected {expected_response}. "
        f"Actual status {response.status_code}. "
        f"Response text {response.content}"
    )

    return response


def consumer_create_request(api_client, request_data, expected_response):
    return consumer_request(
        reverse("resource-request-create-consumer"),
        api_client,
        request_data,
        expected_response,
    )


def consumer_update_request(api_client, request_data, expected_response):
    return consumer_request(
        reverse("resource-request-update-consumer"),
        api_client,
        request_data,
        expected_response,
    )


def consumer_delete_request(api_client, request_data, expected_response):
    return consumer_request(
        reverse("resource-request-on-end"),
        api_client,
        request_data,
        expected_response,
    )


@pytest.mark.parametrize(
    "allocation_hours,request_data",
    [
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("flavor_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_flavor_create_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    # Allocate resource credit
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    # Create
    consumer_create_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Find consumer and assert fields are correct
    new_consumer = models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).first()
    assert new_consumer is not None
    assert new_consumer.resource_provider_account == resource_provider_account
    assert new_consumer.user_ref == uuid.UUID(request.config.USER_REF)
    assert new_consumer.start == request.config.START_DATE
    assert new_consumer.end == request.config.END_DATE

    # Check credit has been subtracted
    for c in models.CreditAllocationResource.objects.all():
        assert (
            c.resource_hours == 0
        ), f"CreditAllocationResource for {c.resource_class.name} is not depleted"

    # Check consumption records are correct
    for resource_class in resource_classes:
        rcr = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=resource_class.id
        )
        assert rcr.resource_hours == allocation_hours[resource_class.name]


@pytest.mark.parametrize(
    "allocation_hours,request_data",
    [
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("flavor_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_flavor_delete_upcoming_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    # Allocate resource credit
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    # Create
    consumer_create_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Delete
    consumer_delete_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Find consumer and check duration is 0.
    new_consumer = models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).first()
    assert new_consumer is not None
    # Don't assert this for now as we are unsure of the behaviour of on_end from blazar.
    # assert new_consumer.end == request.config.START_DATE

    # Check our original allocations are intact.
    for resource_class in resource_classes:
        c = models.CreditAllocationResource.objects.filter(
            resource_class=resource_class.id
        ).first()
        assert c.resource_hours == allocation_hours[resource_class.name], (
            f"CreditAllocationResource for {c.resource_class.name} has changed, "
            f"new amount: {c.resource_hours}"
        )


@pytest.mark.parametrize(
    "allocation_hours,request_data",
    [
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("start_early_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_flavor_delete_current_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    # Allocate resource credit
    create_credit_allocation_resources(
        credit_allocation(
            start_date=request.config.START_EARLY_DATE, end_date=request.config.END_DATE
        ),
        resource_classes,
        allocation_hours,
    )

    # Create
    consumer_create_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Delete
    consumer_delete_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Find consumer and check end date is changed.
    new_consumer = models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).first()
    assert new_consumer is not None

    # END_EARLY_DATE is 3/4 the duration of the original allocation.
    # on_end will set the end_time to datetime.now()
    # so we should have consumed 75% of the reservation
    # and refunded 25%.

    # Check our allocations are correct.
    for resource_class in resource_classes:
        c = models.CreditAllocationResource.objects.filter(
            resource_class=resource_class.id
        ).first()
        assert c.resource_hours == allocation_hours[resource_class.name] * 0.25

    # Check consumption records are correct
    for resource_class in resource_classes:
        rcr = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=resource_class.id
        )
        assert rcr.resource_hours == pytest.approx(
            allocation_hours[resource_class.name] * 0.75, 0.5
        )


@pytest.mark.parametrize(
    "allocation_hours,request_data,shorten_request_data",
    [
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("flavor_request_data"),
            lazy_fixture("flavor_shorten_current_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_flavor_shorten_currently_active_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    shorten_request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    # Allocate resource credit
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    # Create
    consumer_create_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Update
    consumer_update_request(
        api_client, shorten_request_data, status.HTTP_204_NO_CONTENT
    )

    # Find consumer and check end date is changed.
    new_consumer = models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).first()
    assert new_consumer is not None
    assert new_consumer.end == request.config.END_EARLY_DATE

    # END_EARLY_DATE is 3/4 the duration of the original allocation.

    # Check our allocations are correct.
    for resource_class in resource_classes:
        c = models.CreditAllocationResource.objects.filter(
            resource_class=resource_class.id
        ).first()
        assert c.resource_hours == allocation_hours[resource_class.name] * 0.25

    # Check consumption records are correct
    for resource_class in resource_classes:
        rcr = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=resource_class.id
        )
        assert rcr.resource_hours == allocation_hours[resource_class.name] * 0.75


@pytest.mark.parametrize(
    "allocation_hours,request_data,delete_request_data",
    [
        (
            {"VCPU": 144, "MEMORY_MB": 36000.0, "DISK_GB": 1260.0},
            lazy_fixture("flavor_request_data"),
            lazy_fixture("flavor_extend_current_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_flavor_extend_currently_active_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    delete_request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    # Allocate resource credit
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    # Create
    consumer_create_request(api_client, request_data, status.HTTP_204_NO_CONTENT)

    # Extend
    consumer_update_request(api_client, delete_request_data, status.HTTP_204_NO_CONTENT)

    # Find consumer and check end date is changed.
    new_consumer = models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).first()
    assert new_consumer is not None
    assert new_consumer.end == request.config.END_LATE_DATE

    # END_LATE_DATE is 1.5x the duration of the original allocation.

    # Check our allocations are correct.
    for resource_class in resource_classes:
        c = models.CreditAllocationResource.objects.filter(
            resource_class=resource_class.id
        ).first()
        assert c.resource_hours == 0

    # Check consumption records are correct
    for resource_class in resource_classes:
        rcr = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=resource_class.id
        )
        assert rcr.resource_hours == allocation_hours[resource_class.name]


@pytest.mark.parametrize(
    "allocation_hours, request_data",
    [
        (
            {"VCPU": 10.0, "MEMORY_MB": 1000.0, "DISK_GB": 100.0},
            lazy_fixture("flavor_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_insufficient_credits_create_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
):
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    consumer_create_request(api_client, request_data, status.HTTP_403_FORBIDDEN)

    # TODO(tylerchristie): assert that allocations have their original values
    assert not models.Consumer.objects.filter(consumer_ref="my_new_lease").exists()
    assert not models.ResourceConsumptionRecord.objects.exists()
    for c in models.CreditAllocationResource.objects.all():
        assert (
            c.resource_hours > 0
        ), f"CreditAllocationResource for {c.resource_class.name} was depleted"


@pytest.mark.parametrize(
    "request_data",
    [
        (lazy_fixture("physical_request_data")),
        (lazy_fixture("virtual_request_data")),
    ],
)
@pytest.mark.django_db
def test_invalid_blazar_resource_type_create_request(
    api_client,
    request_data,
):
    consumer_create_request(api_client, request_data, status.HTTP_400_BAD_REQUEST)


@pytest.mark.parametrize(
    "allocation_hours,request_data",
    [
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("zero_hours_request_data"),
        ),
        (
            {"VCPU": 96.0, "MEMORY_MB": 24000.0, "DISK_GB": 840.0},
            lazy_fixture("negative_hours_request_data"),
        ),
    ],
)
@pytest.mark.django_db
def test_invalid_duration_create_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
):
    create_credit_allocation_resources(
        credit_allocation(), resource_classes, allocation_hours
    )

    response = consumer_create_request(
        api_client, request_data, status.HTTP_403_FORBIDDEN
    )

    print(response.content)


@pytest.mark.parametrize(
    "allocation_hours,existing_request,new_request,expected_status",
    [
        # Front overlap with heavy existing usage (should fail)
        (
            {"VCPU": 96.0 * 7, "MEMORY_MB": 24000.0 * 7, "DISK_GB": 840.0 * 7},
            lazy_fixture("existing_front_heavy_request"),
            lazy_fixture("flavor_request_data"),
            status.HTTP_403_FORBIDDEN,
        ),
        # Back overlap with heavy existing usage (should fail)
        (
            {"VCPU": 96.0 * 7, "MEMORY_MB": 24000.0 * 7, "DISK_GB": 840.0 * 7},
            lazy_fixture("existing_back_heavy_request"),
            lazy_fixture("flavor_request_data"),
            status.HTTP_403_FORBIDDEN,
        ),
    ],
)
@pytest.mark.django_db
def test_quota_check_fails_with_existing(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    existing_request,
    new_request,
    allocation_hours,
    expected_status,
    use_quota_settings,
    request,  # contains pytest global vars
):
    """Test that new requests are rejected when existing usage is too high"""
    # Setup initial allocation
    create_credit_allocation_resources(
        credit_allocation(
            start_date=request.config.PERIOD_START, end_date=request.config.PERIOD_END
        ),
        resource_classes,
        allocation_hours,
    )

    print(request.config.PERIOD_START)
    print("REQUEST:", existing_request)

    # Create existing reservation
    consumer_create_request(api_client, existing_request, status.HTTP_204_NO_CONTENT)

    # Try to create new reservation
    consumer_create_request(api_client, new_request, expected_status)

    # Verify only existing reservation exists
    assert models.Consumer.objects.filter(
        consumer_ref=existing_request["lease"]["name"]
    ).exists()
    assert not models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).exists()


@pytest.mark.parametrize(
    "allocation_hours,existing_request,new_request,expected_status",
    [
        # Front overlap with light existing usage (should succeed)
        (
            {"VCPU": 96.0 * 7, "MEMORY_MB": 24000.0 * 7, "DISK_GB": 840.0 * 7},
            lazy_fixture("existing_front_light_request"),
            lazy_fixture("flavor_request_data"),
            status.HTTP_204_NO_CONTENT,
        ),
        # Back overlap with light existing usage (should succeed)
        (
            {"VCPU": 96.0 * 7, "MEMORY_MB": 24000.0 * 7, "DISK_GB": 840.0 * 7},
            lazy_fixture("existing_back_light_request"),
            lazy_fixture("flavor_request_data"),
            status.HTTP_204_NO_CONTENT,
        ),
    ],
)
@pytest.mark.django_db
def test_quota_check_succeeds_with_existing(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    existing_request,
    new_request,
    allocation_hours,
    expected_status,
    use_quota_settings,
    request,
):
    """Test that new requests are accepted when existing usage is low enough"""
    # Setup initial allocation
    create_credit_allocation_resources(
        credit_allocation(
            start_date=request.config.PERIOD_START, end_date=request.config.PERIOD_END
        ),
        resource_classes,
        allocation_hours,
    )

    # Create existing reservation
    consumer_create_request(api_client, existing_request, status.HTTP_204_NO_CONTENT)

    # Try to create new reservation
    consumer_create_request(api_client, new_request, expected_status)

    # Verify both reservations exist
    assert models.Consumer.objects.filter(
        consumer_ref=existing_request["lease"]["name"]
    ).exists()
    assert models.Consumer.objects.filter(
        consumer_ref=request.config.LEASE_NAME
    ).exists()
