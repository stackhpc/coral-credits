from nest.core.decorators import async_db_request_handler
from pydantic import parse_obj_as
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from coral_credits import db
from coral_credits import objects


class ResourceClassProvider:
    @async_db_request_handler
    async def add_resource_class(
        self, resource_class: objects.ResourceClass, session: AsyncSession
    ) -> objects.ResourceClass:
        db_resource_class = db.ResourceClass(**resource_class.dict())
        session.add(db_resource_class)
        await session.commit()
        return objects.ResourceClass.from_orm(db_resource_class)

    @async_db_request_handler
    async def get_resource_classes(
        self, session: AsyncSession
    ) -> List[objects.ResourceClass]:
        query = sqlalchemy.select(db.ResourceClass)
        result = await session.execute(query)
        return [objects.ResourceClass.from_orm(item) for item in result.scalars().all()]
