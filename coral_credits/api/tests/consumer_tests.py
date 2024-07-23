import json
import uuid

from django.urls import reverse
import pytest
from rest_framework import status

import coral_credits.api.models as models


@pytest.mark.parametrize(
    "allocation_hours",
    [
        ({"vcpu": 96.0, "memory": 24000.0, "disk": 840.0}),
    ],
)
@pytest.mark.django_db
def test_valid_create_request(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
    request,  # contains pytest global vars
):
    START_DATE = request.config.START_DATE
    END_DATE = request.config.END_DATE
    USER_REF = request.config.USER_REF

    credit_allocation_resources = create_credit_allocation_resources(
        credit_allocation, resource_classes, allocation_hours
    )

    url = reverse("resourcerequest-list")
    response = api_client.post(
        url,
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT, (
        f"Expected {status.HTTP_204_NO_CONTENT}. "
        f"Actual status {response.status_code}. "
        f"Response text {response.content}"
    )

    new_consumer = models.Consumer.objects.filter(consumer_ref="my_new_lease").first()
    assert new_consumer is not None
    assert new_consumer.resource_provider_account == resource_provider_account
    assert new_consumer.user_ref == uuid.UUID(USER_REF)
    assert new_consumer.start == START_DATE
    assert new_consumer.end == END_DATE

    for c in models.CreditAllocationResource.objects.all():
        assert (
            c.resource_hours == 0
        ), f"CreditAllocationResource for {c.resource_class.name} is not depleted"

    vcpu, memory, disk = resource_classes
    rcr_vcpu = models.ResourceConsumptionRecord.objects.get(
        consumer=new_consumer, resource_class=vcpu
    )
    assert rcr_vcpu.resource_hours == 96.0

    rcr_memory = models.ResourceConsumptionRecord.objects.get(
        consumer=new_consumer, resource_class=memory
    )
    assert rcr_memory.resource_hours == 24000.0

    rcr_disk = models.ResourceConsumptionRecord.objects.get(
        consumer=new_consumer, resource_class=disk
    )
    assert rcr_disk.resource_hours == 840.0

    vcpu_allocation, memory_allocation, disk_allocation = credit_allocation_resources
    assert vcpu_allocation.resource_hours == rcr_vcpu.resource_hours
    assert memory_allocation.resource_hours == rcr_memory.resource_hours
    assert disk_allocation.resource_hours == rcr_disk.resource_hours


@pytest.mark.parametrize(
    "allocation_hours",
    [
        ({"vcpu": 10.0, "memory": 1000.0, "disk": 100.0}),
    ],
)
@pytest.mark.django_db
def test_create_request_insufficient_credits(
    resource_classes,
    credit_allocation,
    create_credit_allocation_resources,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
):

    credit_allocation_resources = create_credit_allocation_resources(
        credit_allocation, resource_classes, allocation_hours
    )

    url = reverse("resourcerequest-list")
    response = api_client.post(
        url,
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"Expected {status.HTTP_403_FORBIDDEN}. "
        f"Actual status {response.status_code}. "
        f"Response text {response.content}"
    )

    # TODO(tylerchristie): assert that allocations have their original values
    assert not models.Consumer.objects.filter(consumer_ref="my_new_lease").exists()
    assert not models.ResourceConsumptionRecord.objects.exists()
    for c in models.CreditAllocationResource.objects.all():
        assert (
            c.resource_hours > 0
        ), f"CreditAllocationResource for {c.resource_class.name} was depleted"
