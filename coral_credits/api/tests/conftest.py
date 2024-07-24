from datetime import datetime, timedelta

from django.utils.timezone import make_aware
import pytest
from rest_framework.test import APIClient

import coral_credits.api.models as models


def pytest_configure(config):
    config.PROJECT_ID = "20354d7a-e4fe-47af-8ff6-187bca92f3f9"
    config.USER_REF = "caa8b54a-eb5e-4134-8ae2-a3946a428ec7"
    config.START_DATE = make_aware(datetime.now())
    config.END_DATE = config.START_DATE + timedelta(days=1)


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
def resource_provider_account(request, account, provider):
    return models.ResourceProviderAccount.objects.create(
        account=account, provider=provider, project_id=request.config.PROJECT_ID
    )


@pytest.fixture
def credit_allocation(account, request):
    return models.CreditAllocation.objects.create(
        account=account,
        name="test",
        start=request.config.START_DATE,
        end=request.config.END_DATE,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_credit_allocation_resources():
    # Factory fixture
    def _create_credit_allocation_resources(
        credit_allocation, resource_classes, allocation_hours
    ):
        vcpu, memory, disk = resource_classes
        vcpu_allocation = models.CreditAllocationResource.objects.create(
            allocation=credit_allocation,
            resource_class=vcpu,
            resource_hours=allocation_hours["vcpu"],
        )
        memory_allocation = models.CreditAllocationResource.objects.create(
            allocation=credit_allocation,
            resource_class=memory,
            resource_hours=allocation_hours["memory"],
        )
        disk_allocation = models.CreditAllocationResource.objects.create(
            allocation=credit_allocation,
            resource_class=disk,
            resource_hours=allocation_hours["disk"],
        )
        return (vcpu_allocation, memory_allocation, disk_allocation)

    return _create_credit_allocation_resources
