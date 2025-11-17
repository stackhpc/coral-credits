import pytest
from tofupy import Tofu
import requests
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import uuid
import json
import tofu_test_data

coral_uri = os.environ.get("TF_VAR_coral_uri")
headers = {"Authorization": "Bearer " + os.environ.get("TF_VAR_auth_token")}


initial_time = datetime.now()
def time_with_month_offset(offset):
    return (datetime.now() + relativedelta(months=offset)).strftime("%Y-%m-%d-%H:%M:%S")

q1_standard_resources = {
    "VCPU": "40000",
    "MEMORY_MB": "4423680",
    "DISK_GB": "108000"
}

q1_extra_resources = {
    "VCPU": "41000",
    "MEMORY_MB": "4424680",
    "DISK_GB": "109000"
}

q1_insufficient_resources = {
    "VCPU": "10",
    "MEMORY_MB": "10",
    "DISK_GB": "10"
}

q1_st = time_with_month_offset(-2)
q1_end = time_with_month_offset(1)
q2_st = time_with_month_offset(12)
q2_end = time_with_month_offset(15)

standard_test_data = tofu_test_data.get_standard_test_vars(
    q1_st,
    q1_end,
    q2_st,
    q2_end,
    q1_standard_resources
    )

updated_test_data = tofu_test_data.get_standard_test_vars(
    q1_st,
    q1_end,
    q2_st,
    q2_end,
    q1_extra_resources
    )

empty_test_data = tofu_test_data.get_empty_test_data_copy(standard_test_data)
try_active_delete_test_data = tofu_test_data.get_no_q1_copy(standard_test_data)

lease_request_json = tofu_test_data.get_lease_request_json(
    time_with_month_offset(-1),
    (initial_time + relativedelta(days=1)).strftime("%Y-%m-%d-%H:%M:%S")
    )

@pytest.fixture(scope="session")
def terraform_rest_setup():
    working_dir = os.path.join(os.path.dirname(__file__), "..")
    var_file = os.path.join(working_dir, "tests", "tofu_configs", "initial.tfvars")
    delete_file = os.path.join(working_dir, "tests", "tofu_configs", "empty.tfvars")

    tf = Tofu(cwd=working_dir)
    tf.init()
    tf.apply(variables=standard_test_data)

    yield tf

    destroy = tf.apply(variables=empty_test_data)
    assert len(destroy.errors) == 0


@pytest.fixture(scope="session")
def add_consumer_request(terraform_rest_setup):
    # Add consumer outside of tofu to simulate requests from Blazar

    consumer = requests.post(
        coral_uri + "/consumer/create",
        headers={
            "Authorization": "Bearer " + os.environ.get("TF_VAR_auth_token"),
            "Content-Type": "application/json",
        },
        json=lease_request_json,
    )
    return dict(status=consumer.status_code, tf_workspace=terraform_rest_setup)

@pytest.fixture(scope="session")
def update_allocation_resources(add_consumer_request):
    workspace = add_consumer_request["tf_workspace"]
    workspace.apply(variables=updated_test_data)
    return dict(tf_workspace=add_consumer_request["tf_workspace"])

@pytest.fixture(scope="session")
def try_delete_active_allocation(update_allocation_resources):
    print("Testing deleting active allocation, will see 403 errors")
    try_delete = update_allocation_resources["tf_workspace"].apply(
        variables = try_active_delete_test_data
    )
    print("End of active allocation delete test")
    return dict(
        error_count=len(try_delete.errors),
        tf_workspace=update_allocation_resources["tf_workspace"],
    )


@pytest.fixture(scope="session")
def try_destroy_with_active_consumers(try_delete_active_allocation):

    print("Testing destroy with active consumer, will see 403 errors")
    try_delete = try_delete_active_allocation["tf_workspace"].apply(
        variables=empty_test_data
    )
    print("End of destroy with active consumers test")
    yield len(try_delete.errors)
    # Undo any destroys
    reapply = try_delete_active_allocation["tf_workspace"].apply(
        variables=standard_test_data
    )
    assert len(reapply.errors) == 0


@pytest.fixture(scope="session")
def delete_consumer(try_destroy_with_active_consumers):
    requests.post(
        coral_uri + "/consumer/on-end",
        headers={
            "Authorization": "Bearer " + os.environ.get("TF_VAR_auth_token"),
            "Content-Type": "application/json",
        },
        json=lease_request_json,
    )
    return


def api_get_request(resource):
    return requests.get(coral_uri + "/" + resource, headers=headers).json()


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

    assert contains_only(account_names, ["TestAccount1", "TestAccount2"])


def test_rpas_created(terraform_rest_setup):
    rpas = api_get_request("resource_provider_account")
    accounts = api_get_request("account")
    rpa_account_urls = [a["account"] for a in rpas]
    account_urls = [a["url"] for a in accounts]
    assert contains_only(rpa_account_urls, account_urls)


def test_allocations_created(terraform_rest_setup):
    allocations = api_get_request("allocation")
    allocations_names = [a["name"] for a in allocations]

    assert contains_only(allocations_names, ["Q1-0", "Q1-1", "Q2-0"])


def test_allocation_user_mappings(terraform_rest_setup):
    allocations = api_get_request("allocation")
    q1_allocations = [a for a in allocations if a["name"][:2] == "Q1"]
    q2_allocations = [a for a in allocations if a["name"][:2] == "Q2"]

    accounts = api_get_request("account")
    account_urls = {a["name"]: a["url"] for a in accounts}

    q1_allocated_accounts = [a["account"] for a in q1_allocations]
    q2_allocated_accounts = [a["account"] for a in q2_allocations]

    assert contains_only(
        q1_allocated_accounts,
        [account_urls["TestAccount1"], account_urls["TestAccount2"]],
    )
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
    return {
        a["resource_class"]["name"]: a["resource_hours"] for a in allocation_resources
    }


def test_only_allocation_resources_returned(terraform_rest_setup):
    allocation_id = api_get_request("allocation")[0]["id"]
    assert len(api_get_request("allocation/" + str(allocation_id) + "/resources")) == 3


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
                # q1-0 = original - 31 days * 24 hours * lease resources
                "Q1-0": {"VCPU": 37024, "MEMORY_MB": 3679680, "DISK_GB": 81960},
                "Q1-1": {"VCPU": 20000, "MEMORY_MB": 2000000, "DISK_GB": 200000},
                "Q2-0": {"VCPU": 80000, "MEMORY_MB": 8000000, "DISK_GB": 300000},
            },
        ),
        (
            "update_allocation_resources",
            {
                # q1-0 after consumption + new resources
                "Q1-0": {"VCPU": 38024, "MEMORY_MB": 3680680, "DISK_GB": 82960},
                "Q1-1": {"VCPU": 20000, "MEMORY_MB": 2000000, "DISK_GB": 200000},
                "Q2-0": {"VCPU": 80000, "MEMORY_MB": 8000000, "DISK_GB": 300000},
            },
        ),
        (
            "delete_consumer",
            {
                # historical consumer consumption data should be preserved
                "Q1-0": {"VCPU": 38024, "MEMORY_MB": 3680680, "DISK_GB": 82960},
                "Q1-1": {"VCPU": 20000, "MEMORY_MB": 2000000, "DISK_GB": 200000},
                "Q2-0": {"VCPU": 80000, "MEMORY_MB": 8000000, "DISK_GB": 300000},
            },
        ),
    ],
)
def test_resource_allocations_have_correct_resources(
    request, fixture_name, expected_resources
):
    request.getfixturevalue(fixture_name)  # needed to dynamically set fixtures
    allocations = api_get_request("allocation")
    allocation_resources = {
        a["name"]: to_resource_map(
            api_get_request("allocation/" + str(a["id"]) + "/resources")
        )
        for a in allocations
    }
    assert allocation_resources["Q1-0"] == expected_resources["Q1-0"]
    assert allocation_resources["Q1-1"] == expected_resources["Q1-1"]
    assert allocation_resources["Q2-0"] == expected_resources["Q2-0"]


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
        tst = api_get_request("allocation/" + str(alloc["id"]) + "/resources")
        assert len(tst) == 3


def test_destroy_with_consumers_fails(try_destroy_with_active_consumers):
    assert try_destroy_with_active_consumers > 0


def test_all_resources_fail_destroy_for_active_consumers(
    try_destroy_with_active_consumers,
):
    assert len(api_get_request("resource_class")) == 3
    assert len(api_get_request("resource_provider")) == 1
    assert len(api_get_request("account")) == 2
    assert len(api_get_request("resource_provider_account")) == 2
    assert (
        len(api_get_request("allocation")) == 2
    )  # Q2 has no active consumers so destroyed
    assert len(api_get_request("consumer")) == 1
