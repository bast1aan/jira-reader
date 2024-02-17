import json
from datetime import datetime
from typing_extensions import Self

from sqlalchemy import String, Text, create_engine, select, Engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session

from bast1aan.jira_reader import settings, entities


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

def set_up() -> None:
    Base.metadata.create_all(_engine())

_eng: Engine | None = None

def _engine() -> Engine:
    global _eng
    if not _eng:
        _eng = create_engine(settings.SQLSTORAGE_SQLITE)
    return _eng

def get_latest_request(url: str) -> entities.Request:
    with Session(_engine()) as session:
        stmt = select(Request).where(Request.url.is_(url)).order_by(Request.requested.desc()).limit(1)
        model = session.scalar(stmt)
        return model.entity

def save_request(request: entities.Request) -> None:
    with Session(_engine()) as session:
        request_model = Request.from_entity(request)
        session.add(request_model)
        session.commit()
