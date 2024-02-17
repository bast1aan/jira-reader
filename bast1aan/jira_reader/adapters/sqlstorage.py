import json
from datetime import datetime
from functools import cached_property

from typing_extensions import Self

from sqlalchemy import String, Text, create_engine, select, Engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session

from bast1aan.jira_reader import settings, entities, Storage


class Base(DeclarativeBase):
    entity: object

class Request(Base):
    __tablename__ = 'requests'

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(255))
    requested: Mapped[datetime]
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

    def set_up(self) -> None:
        Base.metadata.create_all(self._engine)

    @cached_property
    def _engine(self) -> Engine:
        return create_engine(settings.SQLSTORAGE_SQLITE)

    def _session(self) -> Session:
        return Session(self._engine)

    def get_latest_request(self, url: str) -> entities.Request:
        with self._session() as session:
            stmt = select(Request).where(Request.url.is_(url)).order_by(Request.requested.desc()).limit(1)
            model = session.scalar(stmt)
            return model.entity

    def save_request(self, request: entities.Request) -> None:
        with self._session() as session:
            request_model = Request.from_entity(request)
            session.add(request_model)
            session.commit()
