import json
from datetime import datetime
from functools import cached_property

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection, AsyncSession, async_sessionmaker
from typing_extensions import Self

from sqlalchemy import String, Text, select, UniqueConstraint, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from bast1aan.jira_reader import settings, entities, Storage


class Base(DeclarativeBase):
    entity: object

class Request(Base):
    __tablename__ = 'requests'
    __table_args__ = (
        UniqueConstraint('url', 'requested'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(255), index=True)
    requested: Mapped[datetime] = mapped_column(DateTime(), index=True)
    result: Mapped[str] = mapped_column(Text())

    @property
    def entity(self) -> entities.Request:
        return entities.Request(
            url=self.url,
            requested=self.requested,
            result=json.loads(self.result)
        )

    @classmethod
    def from_entity(cls, entity: entities.Request) -> Self:
        return cls(
            url=entity.url,
            requested=entity.requested or datetime.now(),
            result=json.dumps(entity.result)
        )

class SQLStorage(Storage):

    async def set_up(self) -> None:
        async with self._async_engine.begin() as conn:
            conn: AsyncConnection
            await conn.run_sync(Base.metadata.create_all)

    @cached_property
    def _async_engine(self) -> AsyncEngine:
        return create_async_engine(settings.SQLSTORAGE_SQLITE)

    @property
    def _async_session(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self._async_engine, expire_on_commit=False)

    async def get_latest_request(self, url: str) -> entities.Request | None:
        async with self._async_session() as session:
            stmt = select(Request).where(Request.url.is_(url)).order_by(Request.requested.desc()).limit(1)
            model = await session.scalar(stmt)
            return model.entity if model else None

    async def save_request(self, request: entities.Request) -> None:
        async with self._async_session() as session:
            request_model = Request.from_entity(request)
            session.add(request_model)
            await session.commit()
