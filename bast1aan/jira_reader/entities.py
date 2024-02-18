from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

JSONable = list | dict | str | None

class Storage(ABC):
    @abstractmethod
    async def get_latest_request(self, url: str) -> Request | None: ...
    @abstractmethod
    async def save_request(self, request: Request) -> None: ...

@dataclass
class Request:
    url: str
    requested: datetime
    result: JSONable

