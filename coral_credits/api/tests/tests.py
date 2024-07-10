import json
from datetime import datetime, timedelta

import django
from django.test import TestCase
from django.urls import reverse
import coral_credits.api.models as models
from rest_framework import status
from rest_framework.test import APIClient

# Create your tests here.
# When using SQLite, the tests will use an in-memory database by default
# https://docs.djangoproject.com/en/5.0/topics/testing/overview/#the-test-database

PROJECT_ID = "12345678-1234-5678-1234-567812345678"
CONSUMER_REF = "test_consumer"
CONSUMER_UUID = "87654321-8765-4321-8765-432187654321"
USER_REF = "98765432-9876-5432-9876-543298765432"
START_DATE = datetime.now()
END_DATE = datetime.now() + timedelta(days=1)


class ResourceRequestTestCase(TestCase):
    def setUp(self):
        # Create resource classes
        self.vcpu = models.ResourceClass.objects.create(name="VCPU")
        self.memory = models.ResourceClass.objects.create(name="MEMORY_MB")
        self.disk = models.ResourceClass.objects.create(name="DISK_GB")

        # Create a resource provider
        self.provider = models.ResourceProvider.objects.create(
            name="Test Provider",
            email="provider@test.com",
            info_url="https://testprovider.com",
        )

        # Create a credit account
        self.account = models.CreditAccount.objects.create(
            email="test@case.com", name="test"
        )

        # Create a credit allocation
        self.credit_allocation = models.CreditAllocation.objects.create(
            account=self.account, name="test", start=START_DATE, end=END_DATE
        )

        # Create credit allocation resources
        self.vcpu_allocation = models.CreditAllocationResource.objects.create(
            allocation=self.credit_allocation,
            resource_class=self.vcpu,
            resource_hours=96.0,
        )
        self.memory_allocation = models.CreditAllocationResource.objects.create(
            allocation=self.credit_allocation,
            resource_class=self.memory,
            # TODO(tylerchristie): memory unit is 1MB currently. we probably want
            # to give it a more operator-friendly unit
            resource_hours=24000.0,
        )
        self.disk_allocation = models.CreditAllocationResource.objects.create(
            allocation=self.credit_allocation,
            resource_class=self.disk,
            resource_hours=840.0,
        )

        # Create a resource provider account
        self.resource_provider_account = models.ResourceProviderAccount.objects.create(
            account=self.account, provider=self.provider, project_id=PROJECT_ID
        )

        # Add APIClient for making requests
        self.client = APIClient()

    def test_create_request(self):
        # Prepare the request data
        request_data = {
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
                                "DISK_GB": {
                                    "allocation_ratio": 1.0,
                                    "max_unit": 35,
                                    "min_unit": 1,
                                    "reserved": 0,
                                    "step_size": 1,
                                    "total": 35,
                                },
                                "MEMORY_MB": {
                                    "allocation_ratio": 1.5,
                                    "max_unit": 1000,
                                    "min_unit": 1,
                                    "reserved": 512,
                                    "step_size": 1,
                                    "total": 1000,
                                },
                                "VCPU": {
                                    "allocation_ratio": 16.0,
                                    "max_unit": 4,
                                    "min_unit": 1,
                                    "reserved": 0,
                                    "step_size": 1,
                                    "total": 4,
                                },
                            },
                            "resource_provider_generation": 7,
                        },
                    }
                ],
            },
        }

        # Make the request to the ConsumerViewSet.create method
        url = reverse("consumer-list")
        response = self.client.post(
            url, data=json.dumps(request_data), content_type="application/json"
        )

        # Check that we get a 204 response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check that all CreditAllocationResource objects are depleted (set to 0)
        for c in models.CreditAllocationResource.objects.all():
            self.assertEqual(
                c.resource_hours,
                0,
                f"CreditAllocationResource for {c.resource_class.name} is not depleted",
            )

        # Verify that a new Consumer object was created
        new_consumer = models.Consumer.objects.filter(
            consumer_ref="my_new_lease"
        ).first()
        self.assertIsNotNone(new_consumer)
        self.assertEqual(
            new_consumer.resource_provider_account, self.resource_provider_account
        )
        self.assertEqual(new_consumer.user_ref, USER_REF)
        self.assertEqual(new_consumer.start, START_DATE)
        self.assertEqual(new_consumer.end, END_DATE)

        # Verify ResourceConsumptionRecord objects were created and check their values
        # TODO(tylerchristie): this will change when we respect the 'max' parameter
        rcr_vcpu = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=self.vcpu
        )
        self.assertEqual(
            rcr_vcpu.resource_hours, 96.0
        )  # 4 VCPUs * 24 hours * 1 (min hosts)

        rcr_memory = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=self.memory
        )
        self.assertEqual(
            rcr_memory.resource_hours, 24000.0
        )  # 1000MB * 24 hours * 1 (min hosts)

        rcr_disk = models.ResourceConsumptionRecord.objects.get(
            consumer=new_consumer, resource_class=self.disk
        )
        self.assertEqual(
            rcr_disk.resource_hours, 840.0
        )  # 35 * 24 hours * 1 (min hosts)

        # Check that the total consumed resources match the initial allocation
        self.assertEqual(self.vcpu_allocation.resource_hours, rcr_vcpu.resource_hours)
        self.assertEqual(
            self.memory_allocation.resource_hours, rcr_memory.resource_hours
        )
        self.assertEqual(self.disk_allocation.resource_hours, rcr_disk.resource_hours)
