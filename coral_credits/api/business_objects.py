from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID


@dataclass
class Context:
    user_id: UUID
    project_id: UUID
    auth_url: str
    region_name: str


@dataclass
class Inventory:
    data: Dict[str, Any]


@dataclass
class ResourceRequest:
    inventories: Inventory
    # TODO(tylerchristie)
    # resource_provider_generation: int = None


@dataclass
class Allocation:
    id: str
    hypervisor_hostname: UUID
    extra: Dict[str, Any]


@dataclass
class Reservation:
    resource_type: str
    min: int
    max: int
    resource_requests: ResourceRequest
    hypervisor_properties: str = None
    resource_properties: str = None
    allocations: List[Allocation] = field(default_factory=list)


@dataclass
class Lease:
    lease_id: UUID
    lease_name: str
    start_date: datetime
    end_time: datetime
    reservations: List[Reservation]

    @property
    def duration(self):
        return (self.end_time - self.start_date).total_seconds() / 3600


@dataclass
class ConsumerRequest:
    context: Context
    lease: Lease
    current_lease: Lease = None
