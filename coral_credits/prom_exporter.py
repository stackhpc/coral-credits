from datetime import datetime
from itertools import chain
import logging

from django.db.utils import OperationalError
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from coral_credits.api import db_utils

LOG = logging.getLogger(__name__)


def get_credit_allocation_date(date_type):
    try:
        accounts = db_utils.get_all_resource_provider_account()
        for a in accounts:
            credit_allocations = db_utils.get_all_credit_allocations(a)
            credit_allocation_resources = db_utils.get_all_credit_allocation_resources(
                credit_allocations
            )
            # map credit allocation by CreditAllocation ID)
            credit_lookup = {alloc.id: alloc for alloc in credit_allocations}
            # project_id, resource_class, provider, days
            for (
                resource_class,
                resource_allocation,
            ) in credit_allocation_resources.items():
                credit_allocation = credit_lookup.get(resource_allocation.allocation)
                # get either 'expires in' or 'valid from' based on date_type parameter.
                days = (getattr(credit_allocation, date_type) - datetime.now()).days()
                yield (str(a.project_id), resource_class.name, a.provider.name, days)
    # Database not yet ready
    except OperationalError as e:
        LOG.warn(f"Database not ready yet: {e}")
    except Exception as e:
        LOG.error(f"Unexpected exception: {e}")


def get_free_hours():
    try:
        accounts = db_utils.get_all_resource_provider_account()
        for a in accounts:
            credit_allocations = db_utils.get_all_credit_allocations(a)
            credit_allocation_resources = db_utils.get_all_credit_allocation_resources(
                credit_allocations
            )
            # project_id, resource_class, provider, resource_hours
            for resource_class, allocation in credit_allocation_resources.items():
                yield (
                    str(a.project_id),
                    resource_class.name,
                    a.provider.name,
                    allocation.resource_hours,
                )
    # Database not yet ready
    except OperationalError as e:
        LOG.warn(f"Database not ready yet: {e}")
    except Exception as e:
        LOG.error(f"Unexpected exception: {e}")


def get_reserved_hours():
    try:
        accounts = db_utils.get_all_resource_provider_account()
        for a in accounts:
            resources = db_utils.get_all_active_reservations(a)
            for resource_class, resource_hours in resources.items():
                # project_id, resource_class, provider, resource_hours
                yield (
                    str(a.project_id),
                    resource_class.name,
                    a.provider.name,
                    resource_hours,
                )
    # Database not yet ready
    except OperationalError as e:
        LOG.warning(f"Database not ready yet: {e}")
    except Exception as e:
        LOG.error(f"Unexpected exception: {e}")


def get_total_hours():
    total_hours = {}

    # TODO(tylerchristie): calling these methods twice, probably more efficient method.
    for item in chain(get_free_hours(), get_reserved_hours()):
        if len(item) != 4:
            LOG.warning(f"Skipping unexpected item: {item}")
            continue
        pid, rc, prov, hours = item
        key = (pid, rc, prov)
        total_hours[key] = total_hours.get(key, 0) + hours

    # project_id, resource_class, provider, resource_hours
    if len(total_hours) > 0:
        for (pid, rc, prov), total_hours in total_hours.items():
            yield pid, rc, prov, total_hours


class CustomCollector(Collector):
    def collect(self):
        coral_credits_allocation_hours_per_project = GaugeMetricFamily(
            "coral_credits_allocation_hours_per_project",
            "Total allocations that are currently active",
            labels=["project_id", "resource_class", "provider"],
        )
        for pid, rc, prov, hours in get_total_hours():
            coral_credits_allocation_hours_per_project.add_metric(
                [pid, rc, prov], hours
            )

        yield coral_credits_allocation_hours_per_project

        coral_credits_allocation_hours_free_per_project = GaugeMetricFamily(
            "coral_credits_allocation_hours_free_per_project",
            "How many hours are free to book",
            labels=["project_id", "resource_class", "provider"],
        )
        for pid, rc, prov, hours in get_free_hours():
            coral_credits_allocation_hours_free_per_project.add_metric(
                [pid, rc, prov], hours
            )

        yield coral_credits_allocation_hours_free_per_project

        coral_credits_allocation_hours_reserved_per_project = GaugeMetricFamily(
            "coral_credits_allocation_hours_reserved_per_project",
            "How many hours are currently reserved",
            labels=["project_id", "resource_class", "provider"],
        )
        for pid, rc, prov, hours in get_reserved_hours():
            coral_credits_allocation_hours_reserved_per_project.add_metric(
                [pid, rc, prov], hours
            )
        yield coral_credits_allocation_hours_reserved_per_project

        # TODO(tylerchristie): leaving this one for now as it's hard
        # coral_credits_allocation_hours_reclaimable_per_project = GaugeMetricFamily(
        #     "coral_credits_allocation_hours_reclaimable_per_project",
        #     "How many hours can be freed up from reservations",
        #     labels=["project_id", "resource_class", "provider"],
        # )
        # yield coral_credits_allocation_hours_reclaimable_per_project

        # coral_credits_allocation_hours_reserved_per_consumer = GaugeMetricFamily(
        #     "coral_credits_allocation_hours_reserved_per_consumer",
        #     "The amount of resource each reservation is allocated.",
        #    labels=["lease_id", "user_id", "project_id", "resource_class", "provider"],
        # )
        # yield coral_credits_allocation_hours_reserved_per_consumer

        # TODO(tylerchristie) question here: technically an account can have
        # multiple CreditAllocations, so is this metric 3 dimensional?
        coral_credits_allocation_hours_expires_in_days_per_project = GaugeMetricFamily(
            "coral_credits_allocation_hours_expires_in_days_per_project",
            "Number of days until the credit allocations expire",
            labels=["project_id", "resource_class", "provider"],
        )
        for pid, rc, prov, hours in get_credit_allocation_date(date_type="end"):
            coral_credits_allocation_hours_expires_in_days_per_project.add_metric(
                [pid, rc, prov], hours
            )

        yield coral_credits_allocation_hours_expires_in_days_per_project

        coral_credits_allocation_hours_valid_since_days_per_project = GaugeMetricFamily(
            "coral_credits_allocation_hours_valid_since_days_per_project",
            "Number of days since the credit allocations became active.",
            labels=["project_id", "resource_class", "provider"],
        )
        for pid, rc, prov, hours in get_credit_allocation_date(date_type="start"):
            coral_credits_allocation_hours_valid_since_days_per_project.add_metric(
                [pid, rc, prov], hours
            )

        yield coral_credits_allocation_hours_valid_since_days_per_project
