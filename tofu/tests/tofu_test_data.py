import copy
import json
import uuid


def get_standard_test_vars(q1_start, q1_end, q2_start, q2_end, q1_0_resources):
    return {
        "resource_provider_name": "Test Provider",
        "resource_provider_email": "testprovider@example.com",
        "resource_provider_info_url": "https://www.google.com",
        "accounts": json.dumps(
            [
                {
                    "name": "TestAccount1",
                    "email": "testaccount1@example.com",
                    "openstack_project_id": "c2eced313b324cdb8e670e6e30bf387d",
                },
                {
                    "name": "TestAccount2",
                    "email": "testaccount2@example.com",
                    "openstack_project_id": "2fbf511968aa443e883a82283b0f0160",
                },
            ]
        ),
        "allocations": json.dumps(
            {
                "Q1": {
                    "start_date": str(q1_start),
                    "end_date": str(q1_end),
                    "projects": [
                        {
                            "account_email": "testaccount1@example.com",
                            "resources": q1_0_resources,
                        },
                        {
                            "account_email": "testaccount2@example.com",
                            "resources": {
                                "VCPU": "20000",
                                "MEMORY_MB": "2000000",
                                "DISK_GB": "200000",
                            },
                        },
                    ],
                },
                "Q2": {
                    "start_date": str(q2_start),
                    "end_date": str(q2_end),
                    "projects": [
                        {
                            "account_email": "testaccount1@example.com",
                            "resources": {
                                "VCPU": "80000",
                                "MEMORY_MB": "8000000",
                                "DISK_GB": "300000",
                            },
                        }
                    ],
                },
            }
        ),
    }


def get_empty_test_data_copy(data):
    tmp = copy.deepcopy(data)
    tmp["allocations"] = "{}"
    tmp["accounts"] = "[]"
    return tmp


def get_no_q1_copy(data):
    tmp = copy.deepcopy(data)
    tmp["allocations"] = json.dumps({"Q2": json.loads(tmp["allocations"])["Q2"]})
    return tmp


def get_lease_request_json(start, end):
    start_time = start
    end_time = end
    return {
        "context": {
            "user_id": "caa8b54a-eb5e-4134-8ae2-a3946a428ec7",
            "project_id": "c2eced313b324cdb8e670e6e30bf387d",
            "auth_url": "http://api.example.com:5000/v3",
            "region_name": "RegionOne",
        },
        "lease": {
            "id": str(uuid.uuid4()),
            "name": "my_new_lease",
            "start_date": start_time,
            "end_date": end_time,
            "reservations": [
                {
                    "amount": 2,
                    "flavor_id": "e26a4241-b83d-4516-8e0e-8ce2665d1966",
                    "resource_type": "flavor:instance",
                    "affinity": None,
                    "allocations": [],
                }
            ],
            "resource_requests": {"DISK_GB": 35, "MEMORY_MB": 1000, "VCPU": 4},
        },
    }
