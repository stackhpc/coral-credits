from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
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


@dataclass(kw_only=True)
class BaseReservation:
    resource_type: str
    allocations: List[Allocation] = field(default_factory=list)


@dataclass(kw_only=True)
class PhysicalReservation(BaseReservation):
    min: int
    max: int
    hypervisor_properties: Optional[str] = None
    resource_properties: Optional[str] = None


@dataclass(kw_only=True)
class FlavorReservation(BaseReservation):
    amount: int
    flavor_id: str
    affinity: str = "None"


@dataclass(kw_only=True)
class VirtualReservation(BaseReservation):
    amount: int
    vcpus: int
    memory_mb: int
    disk_gb: int
    affinity: str = "None"
    resource_properties: Optional[str] = None


@dataclass
class Lease:
    id: UUID
    name: str
    start_date: datetime
    end_date: datetime
    reservations: List[BaseReservation]
    resource_requests: ResourceRequest

    @property
    def duration(self):
        return (self.end_date - self.start_date).total_seconds() / 3600


@dataclass
class ConsumerRequest:
    context: Context
    lease: Lease
    current_lease: Lease = None
