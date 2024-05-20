import json
from datetime import datetime
from functools import cached_property

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection, AsyncSession, async_sessionmaker
from typing_extensions import Self

from sqlalchemy import String, Text, select, UniqueConstraint, DateTime, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from bast1aan.jira_reader import settings, entities, Storage, json_mapper


class Base(DeclarativeBase):
    entity: object

class Request(Base):
    __tablename__ = 'requests'
    __table_args__ = (
        UniqueConstraint('issue', 'requested'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    issue: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    requested: Mapped[datetime] = mapped_column(DateTime(), index=True, nullable=False)
    result: Mapped[str] = mapped_column(Text(), nullable=False)

    @property
    def entity(self) -> entities.Request:
        return entities.Request(
            issue=self.issue,
            requested=self.requested,
            result=json.loads(self.result)
        )

    @classmethod
    def from_entity(cls, entity: entities.Request) -> Self:
        return cls(
            issue=entity.issue,
            requested=entity.requested or datetime.now(),
            result=json_mapper.dumps(entity.result)
        )

class SQLStorage(Storage):

    async def set_up(self) -> None:
        async with self._async_engine.begin() as conn:
            conn: AsyncConnection
            await conn.run_sync(Base.metadata.create_all)

    async def clean_up(self):
        async with self._async_session() as session:
            await session.execute(text('DELETE FROM requests'))

    @cached_property
    def _async_engine(self) -> AsyncEngine:
        return create_async_engine(settings.SQLSTORAGE_SQLITE)

    @property
    def _async_session(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self._async_engine, expire_on_commit=False)

    async def get_latest_request(self, issue: str) -> entities.Request | None:
        async with self._async_session() as session:
            stmt = select(Request).where(Request.issue.is_(issue)).order_by(Request.requested.desc()).limit(1)
            model = await session.scalar(stmt)
            return model.entity if model else None

    async def save_request(self, request: entities.Request) -> None:
        async with self._async_session() as session:
            request_model = Request.from_entity(request)
            session.add(request_model)
            await session.commit()
