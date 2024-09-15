from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

JSONable = list | dict | str | None

class Storage(ABC):
    @abstractmethod
    async def get_latest_request(self, issue: str) -> Request | None: ...
    @abstractmethod
    async def save_request(self, request: Request) -> None: ...
    @abstractmethod
    async def get_issue_data(self, issue: str) -> IssueData: ...
    @abstractmethod
    async def save_issue_data(self, data: IssueData) -> None: ...

@dataclass
class Request:
    issue: str
    result: JSONable
    requested: datetime | None = None

@dataclass
class IssueData:
    issue: str
    history: JSONable
    computed: datetime | None = None

@dataclass
class Timeline:
    TYPE_ASSIGNED_2ND_DEVELOPER = 'assigned_2nd developer'
    TYPE_ASSIGNED = 'assigned'
    TYPE_IN_PROGESS = 'in_progress'
    issue: str
    start: datetime
    end: datetime
    display_name: str
    email: str
    type: str
