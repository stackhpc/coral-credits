from nest import core as nest_core
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from coral_credits import objects
from coral_credits.providers.resource_class import ResourceClassProvider


@nest_core.Controller("resource_classes")
class ResourceClassController:
    service: ResourceClassProvider = nest_core.Depends(ResourceClassProvider)

    @nest_core.Get("/")
    async def get_resource_classes(
        self, session: AsyncSession = nest_core.Depends(config.get_db)
    ):
        return await self.service.get_resource_classes(session)

    @nest_core.Post("/")
    async def add_resource_class(
        self,
        resource_class: objects.ResourceClass,
        session: AsyncSession = nest_core.Depends(config.get_db),
    ):
        return await self.service.add_resource_class(resource_class, session)
