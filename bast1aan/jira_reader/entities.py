from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

JSONable = list | dict | str | None

class Storage(ABC):
    @abstractmethod
    async def get_latest_request(self, issue: str) -> Request | None: ...
    @abstractmethod
    async def save_request(self, request: Request) -> None: ...
    @abstractmethod
    async def get_issue_data(self, issue: str) -> IssueData: ...
    @abstractmethod
    async def save_issue_data(self, data: IssueData) -> IssueData: ...
    @abstractmethod
    async def get_issue_datas(self) -> AsyncIterator[IssueData]: ...
    @abstractmethod
    async def get_recent_issue_datas(self) -> AsyncIterator[IssueData]: ...

@dataclass
class Request:
    issue: str
    result: JSONable
    requested: datetime | None = None

@dataclass
class IssueData:
    issue: str
    history: JSONable
    issue_id: int
    project_id: int
    summary: str
    computed: datetime | None = None

@dataclass(frozen=True)
class Timeline:
    TYPE_ASSIGNED_2ND_DEVELOPER = 'assigned_2nd_developer'
    TYPE_ASSIGNED = 'assigned'
    TYPE_IN_PROGESS = 'in_progress'
    TYPE_WRITING_COMMENT = 'writing_comment'
    issue: str
    start: datetime
    end: datetime
    display_name: str
    email: str
    type: str
    issue_summary: str
