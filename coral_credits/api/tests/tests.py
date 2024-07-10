import json
from datetime import datetime, timedelta
import uuid

import coral_credits.api.models as models
from django.urls import reverse
from django.utils.timezone import make_aware
import pytest
from rest_framework import status
from rest_framework.test import APIClient

PROJECT_ID = "20354d7a-e4fe-47af-8ff6-187bca92f3f9"
USER_REF = "caa8b54a-eb5e-4134-8ae2-a3946a428ec7"
START_DATE = make_aware(datetime.now())
END_DATE = START_DATE + timedelta(days=1)


# Fixtures defining all the necessary database entries for testing
@pytest.fixture
def resource_classes():
    vcpu = models.ResourceClass.objects.create(name="VCPU")
    memory = models.ResourceClass.objects.create(name="MEMORY_MB")
    disk = models.ResourceClass.objects.create(name="DISK_GB")
    return vcpu, memory, disk


@pytest.fixture
def provider():
    return models.ResourceProvider.objects.create(
        name="Test Provider",
        email="provider@test.com",
        info_url="https://testprovider.com",
    )


@pytest.fixture
def account():
    return models.CreditAccount.objects.create(email="test@case.com", name="test")


@pytest.fixture
def resource_provider_account(account, provider):
    return models.ResourceProviderAccount.objects.create(
        account=account, provider=provider, project_id=PROJECT_ID
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def request_data():
    return {
        "context": {
            "user_id": USER_REF,
            "project_id": PROJECT_ID,
            "auth_url": "https://api.example.com:5000/v3",
            "region_name": "RegionOne",
        },
        "lease": {
            "lease_id": "e96b5a17-ada0-4034-a5ea-34db024b8e04",
            "lease_name": "my_new_lease",
            "start_date": START_DATE.isoformat(),
            "end_time": END_DATE.isoformat(),
            "reservations": [
                {
                    "resource_type": "physical:host",
                    "min": 1,
                    "max": 3,
                    "resource_requests": {
                        "inventories": {
                            "DISK_GB": {"total": 35},
                            "MEMORY_MB": {"total": 1000},
                            "VCPU": {"total": 4},
                        },
                        "resource_provider_generation": 7,
                    },
                }
            ],
        },
    }


# credit allocation is parameterised so we can test for sufficient/insufficient credits
def create_credit_allocation(account, resource_classes, allocation_hours):
    allocation = models.CreditAllocation.objects.create(
        account=account, name="test", start=START_DATE, end=END_DATE
    )
    vcpu, memory, disk = resource_classes
    vcpu_allocation = models.CreditAllocationResource.objects.create(
        allocation=allocation,
        resource_class=vcpu,
        resource_hours=allocation_hours["vcpu"],
    )
    memory_allocation = models.CreditAllocationResource.objects.create(
        allocation=allocation,
        resource_class=memory,
        resource_hours=allocation_hours["memory"],
    )
    disk_allocation = models.CreditAllocationResource.objects.create(
        allocation=allocation,
        resource_class=disk,
        resource_hours=allocation_hours["disk"],
    )
    return allocation, (vcpu_allocation, memory_allocation, disk_allocation)


@pytest.mark.parametrize(
    "allocation_hours,expected_status",
    [
        ({"vcpu": 96.0, "memory": 24000.0, "disk": 840.0}, status.HTTP_204_NO_CONTENT),
        ({"vcpu": 10.0, "memory": 1000.0, "disk": 100.0}, status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_create_request(
    resource_classes,
    provider,
    account,
    resource_provider_account,
    api_client,
    request_data,
    allocation_hours,
    expected_status,
):
    allocation, credit_allocation_resources = create_credit_allocation(
        account, resource_classes, allocation_hours
    )

    url = reverse("resourcerequest-list")
    response = api_client.post(
        url,
        data=json.dumps(request_data),
        content_type="application/json",
    )

    assert response.status_code == expected_status, (
        f"Expected {expected_status}. "
        f"Actual status {response.status_code}. "
        f"Response text {response.content}"
    )

    if expected_status == status.HTTP_204_NO_CONTENT:
        new_consumer = models.Consumer.objects.filter(
            consumer_ref="my_new_lease"
        ).first()
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

        vcpu_allocation, memory_allocation, disk_allocation = (
            credit_allocation_resources
        )
        assert vcpu_allocation.resource_hours == rcr_vcpu.resource_hours
        assert memory_allocation.resource_hours == rcr_memory.resource_hours
        assert disk_allocation.resource_hours == rcr_disk.resource_hours
    else:
        # TODO(tylerchristie): assert that allocations have their original values
        assert not models.Consumer.objects.filter(consumer_ref="my_new_lease").exists()
        assert not models.ResourceConsumptionRecord.objects.exists()
        for c in models.CreditAllocationResource.objects.all():
            assert (
                c.resource_hours > 0
            ), f"CreditAllocationResource for {c.resource_class.name} was depleted"
