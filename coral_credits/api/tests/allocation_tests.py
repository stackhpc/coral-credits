from django.urls import reverse
import pytest
from rest_framework import status

import coral_credits.api.models as models


@pytest.fixture
def request_data():
    return {
        "VCPU": 50,
        "MEMORY_MB": 2000,
        "DISK_GB": 1000,
    }


@pytest.mark.django_db
def test_credit_allocation_resource_create_success(
    credit_allocation,
    resource_classes,
    api_client,
    request_data,
):
    allocation = credit_allocation()
    # Prepare data for the API call
    url = reverse("allocation-resource-list", kwargs={"allocation_pk": allocation.id})

    # Make the API call
    response = api_client.post(url, request_data, format="json", secure=True)

    # Check that the request was successful
    assert response.status_code == status.HTTP_200_OK, (
        f"Expected {status.HTTP_200_OK}. "
        f"Actual status {response.status_code}. "
        f"Response text {response.content}"
    )

    # Check database entries are as expected
    # First check we have the number that we expect
    total_cars = models.CreditAllocationResource.objects.filter(allocation=allocation)
    assert len(total_cars) == len(request_data)
