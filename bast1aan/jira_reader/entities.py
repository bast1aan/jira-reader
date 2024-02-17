from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

JSON = list | dict | str

class Storage(ABC):
    @abstractmethod
    def get_latest_request(self, url: str) -> Request: ...
    @abstractmethod
    def save_request(self, request: Request) -> None: ...

@dataclass
class Request:
    url: str
    requested: datetime
    result: JSON

