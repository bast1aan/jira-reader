from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase): pass

class Request(Base):
    __tablename__ = 'requests'

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(255))
    requested: Mapped[datetime]
    result: Mapped[str] = mapped_column(Text())
