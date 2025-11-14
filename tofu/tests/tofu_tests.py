import pytest
from tofupy import Tofu
import requests
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import uuid

coral_uri = os.environ.get("TF_VAR_coral_uri")
headers = {"Authorization": "Bearer "+os.environ.get("TF_VAR_auth_token")}

def get_lease_request_json():
    start_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    end_time = (datetime.now() + relativedelta(months=1)).strftime("%Y-%m-%d-%H:%M:%S")
    return {
            "context": {
                "user_id": "caa8b54a-eb5e-4134-8ae2-a3946a428ec7",
                "project_id": "c2eced313b324cdb8e670e6e30bf387d",
                "auth_url": "http://api.example.com:5000/v3",
                "region_name": "RegionOne"
            },
            "lease": {
                "id": str(uuid.uuid4()),
                "name": "my_new_lease",
                "start_date": start_time,
                "end_date": end_time,
                "reservations": [
                    {   "amount": 2,
                        "flavor_id": "e26a4241-b83d-4516-8e0e-8ce2665d1966", 
                        "resource_type": "flavor:instance",
                        "affinity" : None,
                        "allocations": []
                    }
                ],
                "resource_requests": {
                    "DISK_GB": 35,
                    "MEMORY_MB": 1000,
                    "VCPU": 4
                }
            }
        }


lease_request_json = get_lease_request_json()

@pytest.fixture(scope="session")
def terraform_rest_setup():
    working_dir = os.path.join(os.path.dirname(__file__), "..")
    var_file = os.path.join(working_dir, "tests", "tofu_configs", "initial.tfvars")
    delete_file = os.path.join(working_dir, "tests", "tofu_configs", "empty.tfvars")
    
    tf = Tofu(cwd=working_dir)
    tf.init()
    tf.apply(extra_args=["--var-file="+var_file])

    yield tf

    destroy = tf.apply(extra_args=["--var-file="+delete_file])
    assert len(destroy.errors) == 0

@pytest.fixture(scope="session")
def add_consumer_request(terraform_rest_setup):
    # Add consumer outside of tofu to simulate requests from Blazar

    consumer = requests.post(coral_uri+"/consumer/create",headers={
            "Authorization": "Bearer "+os.environ.get("TF_VAR_auth_token"),
            "Content-Type": "application/json"
        },
        json=lease_request_json
    )
    yield dict(status = consumer.status_code, tf_workspace = terraform_rest_setup)
    requests.post(coral_uri+"/consumer/on-end",headers={
            "Authorization": "Bearer "+os.environ.get("TF_VAR_auth_token"),
            "Content-Type": "application/json"
        },
        json=lease_request_json
    )

@pytest.fixture(scope="session")
def try_delete_active_allocation(add_consumer_request):
    delete_file = os.path.join(os.path.dirname(__file__), "..", "tests", "tofu_configs", "delete-active.tfvars")
    try_delete = add_consumer_request["tf_workspace"].apply(extra_args=["--var-file="+delete_file])
    return dict(error_count = len(try_delete.errors),tf_workspace = add_consumer_request["tf_workspace"])

@pytest.fixture(scope="session")
def try_destroy_with_active_consumers(try_delete_active_allocation):
    all_file = os.path.join(os.path.dirname(__file__), "..", "tests", "tofu_configs", "initial.tfvars")
    delete_file = os.path.join(os.path.dirname(__file__), "..", "tests", "tofu_configs", "empty.tfvars")
    try_delete = try_delete_active_allocation["tf_workspace"].apply(extra_args=["--var-file="+delete_file])
    yield len(try_delete.errors)
    # Undo any destroys
    reapply = try_delete_active_allocation["tf_workspace"].apply(extra_args=["--var-file="+all_file])
    assert len(reapply.errors) == 0


def api_get_request(resource):
    return requests.get(coral_uri+"/"+resource,headers=headers).json()

def contains_only(actual, expected):
    return len(actual) == len(expected) and set(expected).issubset(actual)

def test_resource_classes_created(terraform_rest_setup):
    resp = api_get_request("resource_class")
    created_resource_classes = [c["name"] for c in resp]

    assert contains_only(created_resource_classes, ["DISK_GB", "MEMORY_MB", "VCPU"])

def test_resource_provider_created(terraform_rest_setup):
    providers = api_get_request("resource_provider")
    provider_names = [p["name"] for p in providers]
    
    assert contains_only(provider_names, ["Test Provider"])

def test_accounts_created(terraform_rest_setup):
    accounts = api_get_request("account")
    account_names = [a["name"] for a in accounts]

    assert contains_only(account_names, ["TestAccount1","TestAccount2"])

def test_rpas_created(terraform_rest_setup):
    rpas = api_get_request("resource_provider_account")
    accounts = api_get_request("account")
    rpa_account_urls = [a["account"] for a in rpas]
    account_urls = [a["url"] for a in accounts]
    assert contains_only(rpa_account_urls, account_urls)

def test_allocations_created(terraform_rest_setup):
    allocations = api_get_request("allocation")
    allocations_names = [a["name"] for a in allocations]

    assert contains_only(allocations_names, ["Q1-0","Q1-1","Q2-0"])

def test_allocation_user_mappings(terraform_rest_setup):
    allocations = api_get_request("allocation")
    q1_allocations = [a for a in allocations if a["name"][:2] == "Q1"]
    q2_allocations = [a for a in allocations if a["name"][:2] == "Q2"]

    accounts = api_get_request("account")
    account_urls = {a["name"]: a["url"] for a in accounts}

    q1_allocated_accounts = [a["account"] for a in q1_allocations]
    q2_allocated_accounts = [a["account"] for a in q2_allocations]

    assert contains_only(q1_allocated_accounts, [account_urls["TestAccount1"],account_urls["TestAccount2"]])
    assert contains_only(q2_allocated_accounts, [account_urls["TestAccount1"]])

def test_allocation_date_mappings(terraform_rest_setup):
    allocations = api_get_request("allocation")
    q1_allocations = [a for a in allocations if a["name"][:2] == "Q1"]
    q2_allocations = [a for a in allocations if a["name"][:2] == "Q2"]

    q1_allocation_starts = [a["start"] for a in q1_allocations]
    q2_allocation_starts = [a["start"] for a in q2_allocations]

    assert len(set(q1_allocation_starts)) == 1
    assert len(q2_allocation_starts) == 1
    assert q1_allocation_starts[0] != q2_allocation_starts[0]

def to_resource_map(allocation_resources):
    return {a["resource_class"]["name"] : a["resource_hours"] for a in allocation_resources}

def test_only_allocation_resources_returned(terraform_rest_setup):
    allocation_id = api_get_request("allocation")[0]["id"]
    assert len(api_get_request("allocation/"+str(allocation_id)+"/resources")) == 3

@pytest.mark.parametrize(
    "fixture_name, expected_resources",
    [
        (
            "terraform_rest_setup",
            {
                "Q1-0": {"VCPU": 40000, "MEMORY_MB": 4423680, "DISK_GB": 108000},
                "Q1-1": {"VCPU": 20000, "MEMORY_MB": 2000000, "DISK_GB": 200000},
                "Q2-0": {"VCPU": 80000, "MEMORY_MB": 8000000, "DISK_GB": 300000},
            },
        ),
        (
            "add_consumer_request",
            {
                # q1-0 = original - resource hours requested for a month by lease
                "Q1-0": {"VCPU": 37120, "MEMORY_MB": 3703680, "DISK_GB": 82800},
                "Q1-1": {"VCPU": 20000, "MEMORY_MB": 2000000, "DISK_GB": 200000},
                "Q2-0": {"VCPU": 80000, "MEMORY_MB": 8000000, "DISK_GB": 300000},
            },
        ),
    ],
)
def test_resource_allocations_have_correct_resources(request, fixture_name,expected_resources):
    request.getfixturevalue(fixture_name) # needed to dynamically set fixtures
    allocations = api_get_request("allocation")
    allocation_resources = {
        a["name"]: to_resource_map(api_get_request("allocation/"+str(a["id"])+"/resources"))
        for a in allocations
    }
    assert allocation_resources["Q1-0"] == expected_resources["Q1-0"]
    assert allocation_resources["Q1-1"] == expected_resources["Q1-1"]
    assert allocation_resources["Q2-0"] == expected_resources["Q2-0"]


def test_resources_still_consumed_after_consumer_delete():
    raise NotImplementedError()

def test_consumer_added_or_exists(add_consumer_request):
    assert add_consumer_request["status"] == 204

def test_can_query_consumer(add_consumer_request):
    assert len(api_get_request("consumer")) == 1

def test_delete_allocation_with_consumer_forbidden(try_delete_active_allocation):
    assert try_delete_active_allocation["error_count"] > 0

def test_delete_active_allocation_resources_fails(try_delete_active_allocation):
    allocations = api_get_request("allocation")
    q1_allocations = [a for a in allocations if a["name"][:2] == "Q1"]
    for alloc in q1_allocations:
        tst = api_get_request("allocation/"+str(alloc["id"])+"/resources")
        assert len(tst) == 3

def test_destroy_with_consumers_fails(try_destroy_with_active_consumers):
    assert try_destroy_with_active_consumers > 0

def test_all_resources_fail_destroy_for_active_consumers(try_destroy_with_active_consumers):
    assert len(api_get_request("resource_class")) == 3
    assert len(api_get_request("resource_provider")) == 1
    assert len(api_get_request("account")) == 2
    assert len(api_get_request("resource_provider_account")) == 2
    assert len(api_get_request("allocation")) == 2 #Q2 has no active consumers so destroyed
    assert len(api_get_request("consumer")) == 1
