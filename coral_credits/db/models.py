import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from config import config


class ResourceClass(config.Base):
    __tablename__ = "resource_class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
