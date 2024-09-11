import json
from abc import ABC, abstractmethod
from asyncio import Future
from datetime import datetime
from functools import cached_property, reduce
from typing import Callable

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection, AsyncSession, async_sessionmaker
from typing_extensions import Self

from sqlalchemy import String, Text, select, UniqueConstraint, DateTime, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from bast1aan.jira_reader import settings, entities, Storage, json_mapper


def _get_aio_url() -> str:
    url: str = settings.SQLSTORAGE_SQLITE
    replaces = {'sqlite:/': 'sqlite+aiosqlite:/'}
    return reduce(lambda a, b: a.replace(b[0], b[1]), replaces.items(), url)


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

class IssueData(Base):
    __tablename__ = 'issue_data'
    __table_args__ = (
        UniqueConstraint('issue', 'computed'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    issue: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    computed: Mapped[datetime] = mapped_column(DateTime(), index=True, nullable=False)
    history: Mapped[str] = mapped_column(Text(), nullable=False)

    @property
    def entity(self) -> entities.IssueData:
        return entities.IssueData(
            issue=self.issue,
            computed=self.computed,
            history=json.loads(self.history),
        )

    @classmethod
    def from_entity(cls, entity: entities.IssueData) -> Self:
        return cls(
            issue=entity.issue,
            computed=entity.computed or datetime.now(),
            history=json_mapper.dumps(entity.history),
        )

class SQLInitializer(ABC):
    @abstractmethod
    async def __call__ (self, conn: AsyncConnection) -> None:...

class SQLStorage(Storage):
    def __init__(self, sql_initializer: SQLInitializer):
        self._sql_initializer = sql_initializer

    async def set_up(self) -> None:
        async with self._async_engine.begin() as conn:
            conn: AsyncConnection
            await self._sql_initializer(conn)

    @cached_property
    def _async_engine(self) -> AsyncEngine:
        return create_async_engine(_get_aio_url())

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

    async def get_issue_data(self, issue: str) -> entities.IssueData:
        async with self._async_session() as session:
            stmt = select(IssueData).where(IssueData.issue.is_(issue)).order_by(IssueData.computed.desc()).limit(1)
            model = await session.scalar(stmt)
            return model.entity if model else None

    async def save_issue_data(self, data: entities.IssueData) -> None:
        async with self._async_session() as session:
            data_model = IssueData.from_entity(data)
            session.add(data_model)
            await session.commit()
