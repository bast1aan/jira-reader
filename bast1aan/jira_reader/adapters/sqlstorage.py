import json
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass
from datetime import datetime
from functools import cached_property, reduce
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection, AsyncSession, async_sessionmaker
from typing_extensions import Self

from sqlalchemy import String, Text, select, UniqueConstraint, DateTime, Integer, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from bast1aan.jira_reader import settings, entities, Storage, json_mapper

from . import datetime as datetime_adapter

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

@dataclass
class SQLIssueDataEntity(entities.IssueData):
    id: InitVar[int | None] = None

    def __post_init__(self, id: int | None):
        self.__id = id

    def get_id(self) -> int | None:
        return self.__id

class IssueData(Base):
    __tablename__ = 'issue_data'
    __table_args__ = (
        UniqueConstraint('issue', 'computed'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    issue: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    computed: Mapped[datetime] = mapped_column(DateTime(), index=True, nullable=False)
    history: Mapped[str] = mapped_column(Text(), nullable=False)
    issue_id: Mapped[int] = mapped_column(Integer(), nullable=True)
    project_id: Mapped[int] = mapped_column(Integer(), nullable=True)
    summary: Mapped[str] = mapped_column(Text(), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    created_by: Mapped[str] = mapped_column(Text(), nullable=True)

    @property
    def entity(self) -> SQLIssueDataEntity:
        return SQLIssueDataEntity(
            id=self.id,
            issue=self.issue,
            computed=self.computed,
            history=json.loads(self.history),
            issue_id=self.issue_id,
            project_id=self.project_id,
            summary=self.summary,
            created=self.created,
            created_by=self.created_by,
        )

    @classmethod
    def from_entity(cls, entity: entities.IssueData) -> Self:
        self = cls()
        self.update_from_entity(entity)
        return self

    def update_from_entity(self, entity: entities.IssueData) -> None:
        self.issue = entity.issue
        self.computed = entity.computed or datetime_adapter.now()
        self.history = json_mapper.dumps(entity.history)
        self.issue_id = entity.issue_id
        self.project_id = entity.project_id
        self.summary = entity.summary
        self.created = entity.created
        self.created_by = entity.created_by

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

    async def get_issue_data(self, issue: str) -> SQLIssueDataEntity:
        async with self._async_session() as session:
            stmt = select(IssueData).where(IssueData.issue.is_(issue)).order_by(IssueData.computed.desc()).limit(1)
            model = await session.scalar(stmt)
            return model.entity if model else None

    async def save_issue_data(self, data: entities.IssueData) -> SQLIssueDataEntity:
        async with self._async_session() as session:
            if isinstance(data, SQLIssueDataEntity) and (id_ := data.get_id()):
                # update existing
                data_model: IssueData = await session.scalar(
                    select(IssueData).where(IssueData.id == id_)
                )
                data_model.update_from_entity(data)
            else:
                data_model = IssueData.from_entity(data)
            session.add(data_model)
            await session.commit()
            return data_model.entity

    async def get_issue_datas(self) -> AsyncIterator[SQLIssueDataEntity]:
        async with self._async_session() as session:
            stmt = select(IssueData).order_by(IssueData.id.asc())
            async for model in await session.stream_scalars(stmt):
                model: IssueData
                yield model.entity

    async def get_recent_issue_datas(self, from_: datetime | None = None) -> AsyncIterator[entities.IssueData]:
        where = ''
        params = {}
        if from_:
            where = 'WHERE issue_data.computed >= :from_'
            params['from_'] = from_
        sql = f"""SELECT issue_data.* FROM issue_data 
        INNER JOIN (SELECT id, issue, MAX(computed) AS max_computed FROM issue_data GROUP BY issue) latest
            ON issue_data.id = latest.id
        {where}    
        ORDER BY issue_data.id ASC"""

        async with self._async_session() as session:
            stmt = select(IssueData).from_statement(text(sql))
            async for model in await session.stream_scalars(stmt, params=params or None):
                model: IssueData
                yield model.entity
