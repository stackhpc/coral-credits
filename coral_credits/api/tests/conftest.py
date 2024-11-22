import copy
from datetime import datetime, timedelta

from django.apps import apps
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

import coral_credits.api.models as models


def pytest_configure(config):
    config.LEASE_NAME = "my_new_lease"
    config.LEASE_ID = "e96b5a17-ada0-4034-a5ea-34db024b8e04"
    config.ALT_LEASE_ID = "f3a8d076-5b2d-4608-9d2e-0ff72eaa3496"
    config.PROJECT_ID = "20354d7a-e4fe-47af-8ff6-187bca92f3f9"
    config.USER_REF = "caa8b54a-eb5e-4134-8ae2-a3946a428ec7"
    config.START_DATE = make_aware(datetime.now())
    config.END_DATE = config.START_DATE + timedelta(days=1)
    config.END_EARLY_DATE = config.START_DATE + timedelta(days=0.75)
    config.END_LATE_DATE = config.START_DATE + timedelta(days=1.5)
    config.START_EARLY_DATE = config.START_DATE + timedelta(days=-0.75)

    # Setting quota period to be a week containing the test dates
    config.PERIOD_START = (
        config.START_DATE - timedelta(days=config.START_DATE.weekday())
    ).replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # Monday
    config.PERIOD_END = config.PERIOD_START + timedelta(days=6)  # Sunday


@pytest.fixture()
def use_quota_settings(settings):
    settings.CORAL_CONFIG = {
        "QUOTA": {"ENABLED": True, "LIMIT_PERIOD": "week", "USAGE_LIMIT": 200}
    }


# Get auth token
@pytest.fixture
def token():
    user = User.objects.create_user(username="testuser", password="12345")
    return Token.objects.create(user=user)


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
    # Factory fixture
    def _credit_allocation(start_date=None, end_date=None):
        return models.CreditAllocation.objects.create(
            account=account,
            name="test",
            start=start_date or request.config.START_DATE,
            end=end_date or request.config.END_DATE,
        )

    return _credit_allocation


@pytest.fixture
def api_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + token.key)
    return client


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
            resource_hours=allocation_hours["VCPU"],
        )
        memory_allocation = models.CreditAllocationResource.objects.create(
            allocation=credit_allocation,
            resource_class=memory,
            resource_hours=allocation_hours["MEMORY_MB"],
        )
        disk_allocation = models.CreditAllocationResource.objects.create(
            allocation=credit_allocation,
            resource_class=disk,
            resource_hours=allocation_hours["DISK_GB"],
        )
        return (vcpu_allocation, memory_allocation, disk_allocation)

    return _create_credit_allocation_resources


#####
# POST-TEST
#####


@pytest.fixture(autouse=True)
def print_db_state():
    """We output the state of the database after a test."""
    # pre-test:
    yield  # this is where the testing happens

    # post-test:
    print("\n----- Database State -----")

    # Get all models from your app
    app_models = apps.get_app_config("api").get_models()

    for model in app_models:
        print(f"\n{model.__name__}:")
        for instance in model.objects.all():
            print(f"  - {instance}")

    print("\n--------------------------")


#####
# REQUEST DATA
#####


@pytest.fixture
def base_request_data(request):
    return {
        "context": {
            "user_id": request.config.USER_REF,
            "project_id": request.config.PROJECT_ID,
            "auth_url": "https://api.example.com:5000/v3",
            "region_name": "RegionOne",
        },
        "lease": {
            "id": request.config.LEASE_ID,
            "name": request.config.LEASE_NAME,
            "start_date": request.config.START_DATE.isoformat(),
            "end_date": request.config.END_DATE.isoformat(),
            "before_end_date": None,
            "reservations": [],
        },
    }


@pytest.fixture
def flavor_request_data(base_request_data):
    flavor_data = {
        "lease": {
            "reservations": [
                {
                    "amount": 2,
                    "flavor_id": "e26a4241-b83d-4516-8e0e-8ce2665d1966",
                    "resource_type": "flavor:instance",
                    "affinity": None,
                    "allocations": [],
                }
            ],
            "resource_requests": {
                "DISK_GB": 35,
                "MEMORY_MB": 1000,
                "VCPU": 4,
            },
        },
    }
    return deep_merge(base_request_data, flavor_data)


@pytest.fixture
def flavor_extend_current_request_data(flavor_request_data, request):
    extend_request_data = {"current_lease": copy.deepcopy(flavor_request_data["lease"])}
    extend_request_data["lease"] = {
        "end_date": request.config.END_LATE_DATE.isoformat()
    }
    return deep_merge(flavor_request_data, extend_request_data)


@pytest.fixture
def flavor_shorten_current_request_data(flavor_request_data, request):
    shorten_request_data = {
        "current_lease": copy.deepcopy(flavor_request_data["lease"])
    }
    shorten_request_data["lease"] = {
        "end_date": request.config.END_EARLY_DATE.isoformat()
    }
    return deep_merge(flavor_request_data, shorten_request_data)


@pytest.fixture
def start_early_request_data(flavor_request_data, request):
    zero_hours_request_data = {
        "lease": {
            "start_date": request.config.START_EARLY_DATE.isoformat(),
            "end_date": (
                request.config.START_EARLY_DATE + timedelta(days=1)
            ).isoformat(),
        }
    }
    return deep_merge(flavor_request_data, zero_hours_request_data)


@pytest.fixture
def zero_hours_request_data(flavor_request_data, request):
    zero_hours_request_data = {
        "lease": {"end_date": request.config.START_DATE.isoformat()}
    }
    return deep_merge(flavor_request_data, zero_hours_request_data)


@pytest.fixture
def negative_hours_request_data(flavor_request_data, request):
    zero_hours_request_data = {
        "lease": {
            "end_date": (request.config.START_DATE - timedelta(days=1)).isoformat()
        }
    }
    return deep_merge(flavor_request_data, zero_hours_request_data)


@pytest.fixture
def physical_request_data(base_request_data):
    physical_request_data = {
        "lease": {
            "reservations": [
                {
                    "resource_type": "physical:host",
                    "min": 1,
                    "max": 2,
                    "hypervisor_properties": "",
                    "resource_properties": "",
                    "allocations": [],
                }
            ],
        },
    }
    return deep_merge(base_request_data, physical_request_data)


@pytest.fixture
def virtual_request_data(base_request_data):
    virtual_request_data = {
        "lease": {
            "reservations": [
                {
                    "resource_type": "virtual:instance",
                    "amount": 1,
                    "vcpus": 1,
                    "memory_mb": 1,
                    "disk_gb": 0,
                    "affinity": None,
                    "resource_properties": "",
                    "allocations": [],
                }
            ],
        },
    }
    return deep_merge(base_request_data, virtual_request_data)


@pytest.fixture
def existing_front_heavy_request(flavor_request_data, request):
    """Existing reservation that uses most of quota at period start"""
    front_heavy_request_data = {
        "lease": {
            "name": "existing-front-heavy",
            "start_date": (request.config.PERIOD_START - timedelta(days=1)).isoformat(),
            "end_date": (request.config.PERIOD_START + timedelta(days=2)).isoformat(),
        }
    }
    return deep_merge(flavor_request_data, front_heavy_request_data)


@pytest.fixture
def existing_front_light_request(flavor_request_data, request):
    """Existing reservation that uses little quota at period start"""
    front_light_request_data = {
        "lease": {
            "id": request.config.ALT_LEASE_ID,
            "name": "existing-front-light",
            "start_date": (request.config.PERIOD_START - timedelta(days=1)).isoformat(),
            "end_date": (request.config.PERIOD_START + timedelta(days=2)).isoformat(),
            "resource_requests": {
                "DISK_GB": 10,
                "MEMORY_MB": 100,
                "VCPU": 1,
            },
        }
    }
    return deep_merge(flavor_request_data, front_light_request_data)


@pytest.fixture
def existing_back_heavy_request(flavor_request_data, request):
    """Existing reservation that uses most of quota at period end"""
    back_heavy_request_data = {
        "lease": {
            "name": "existing-back-heavy",
            "start_date": (request.config.PERIOD_END - timedelta(days=2)).isoformat(),
            "end_date": (request.config.PERIOD_END + timedelta(days=1)).isoformat(),
        }
    }
    return deep_merge(flavor_request_data, back_heavy_request_data)


@pytest.fixture
def existing_back_light_request(flavor_request_data, request):
    """Existing reservation that uses little quota at period end"""
    back_light_request_data = {
        "lease": {
            "id": request.config.ALT_LEASE_ID,
            "name": "existing-back-light",
            "start_date": (request.config.PERIOD_END - timedelta(days=2)).isoformat(),
            "end_date": (request.config.PERIOD_END + timedelta(days=1)).isoformat(),
            "resource_requests": {
                "DISK_GB": 10,
                "MEMORY_MB": 100,
                "VCPU": 1,
            },
        }
    }
    return deep_merge(flavor_request_data, back_light_request_data)


def deep_merge(defaults, overrides=None):
    """Recursively merge two dictionaries."""
    result = defaults.copy()
    if overrides:
        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
    return result
