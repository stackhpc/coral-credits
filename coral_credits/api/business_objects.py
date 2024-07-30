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
class ResourceRequest:
    resources: Dict[str, Any]


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
    hypervisor_properties: str = None
    resource_properties: str = None
    allocations: List[Allocation] = field(default_factory=list)


@dataclass
class Lease:
    id: UUID
    name: str
    start_date: datetime
    end_date: datetime
    reservations: List[Reservation]
    resource_requests: ResourceRequest

    @property
    def duration(self):
        return (self.end_date - self.start_date).total_seconds() / 3600


@dataclass
class ConsumerRequest:
    context: Context
    lease: Lease
    current_lease: Lease = None
