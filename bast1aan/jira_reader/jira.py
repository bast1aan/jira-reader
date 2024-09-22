from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import StrEnum, auto, Enum
from typing import Mapping, TypeVar, Iterator, Iterable

from .entities import IssueData, Timeline
from .json_mapper import JsonMapper, into, asdataclass
from .reader import Action
from . import settings

T = TypeVar('T')

@dataclass
class JiraAction(Action[T]):
    HOST = settings.JIRA_HOST
    AUTH_LOGIN = settings.JIRA_EMAIL
    AUTH_PASSWORD = settings.JIRA_API_TOKEN
    @property
    def url_args(self) -> Mapping[str, str]:
        return asdict(self)

@dataclass
class RequestTicketData(JiraAction[object]):
    URL = '/rest/api/3/issue/{issue}?expand=renderedFields,changelog'
    issue: str
    def mapper(self, data: object) -> object:
        return data

class ComputeTicketHistory(JiraAction["ComputeTicketHistory.Response"]):
    @dataclass
    class Response:
        @dataclass
        class Item:
            @dataclass
            class Action:
                field: str
                toString: str | None
                fromString: str | None

            byEmailAddress: str | None
            byDisplayName: str
            created: datetime
            actions: list[ComputeTicketHistory.Response.Item.Action]
        @dataclass
        class Comment:
            id: int
            byEmailAddress: str
            byDisplayName: str
            created: datetime
            updated: datetime

        items: list[Item]
        comments: list[Comment]

    URL = ''
    mapper = JsonMapper({
        'changelog': {
            'histories': [{
                'author': {
                    'emailAddress': into(Response.Item).byEmailAddress,
                    'displayName': into(Response.Item).byDisplayName,
                },
                'items': [{
                   'field': into(Response.Item.Action).field,
                   'toString': into(Response.Item.Action).toString,
                   'fromString': into(Response.Item.Action).fromString,
                }, into(Response.Item).actions],
                'created': into(Response.Item).created,
            }, into(Response).items],
        },
        "renderedFields": {
            'comment': {
                'comments': [{
                    'id': into(Response.Comment).id,
                    'author': {
                        'emailAddress': into(Response.Comment).byEmailAddress,
                        'displayName': into(Response.Comment).byDisplayName,
                    },
                    "created": into(Response.Comment).created,
                    "updated": into(Response.Comment).updated,
                }, into(Response).comments]
            }
        }
    })

def calculate_timelines(issue_data: IssueData, filter_display_name: str) -> Iterator[Timeline]:

    @dataclass
    class Event:
        class Type(Enum):
            ASSIGNED = auto()
            UNASSIGNED = auto()
            ASSIGNED_2ND_DEVELOPER = auto()
            UNASSIGNED_2ND_DEVELOPER = auto()
            TO_IN_PROGRESS = auto()
            NO_LONGER_IN_PROGRESS = auto()
        timestamp: datetime
        type: Type

    class ActionState(ABC):
        def __init__(self, main: CalculateTimelines):
            self.main = main
        @abstractmethod
        def process_action(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action) -> None:
            ...
        @abstractmethod
        def process_events(self) -> Iterator[Timeline]:
            ...

    class SecondDeveloper(ActionState):
        _second_developer: datetime = None

        def process_action(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action) -> None:
            if action.field == '2nd Developer':
                if action.toString == self.main.filter_display_name:
                    self.main.event_queue.append(Event(item.created, Event.Type.ASSIGNED_2ND_DEVELOPER))
                if action.fromString == self.main.filter_display_name:
                    self.main.event_queue.append(Event(item.created, Event.Type.UNASSIGNED_2ND_DEVELOPER))

        def process_events(self) -> Iterator[Timeline]:
            for event in self.main.event_queue:
                if event.type == Event.Type.ASSIGNED_2ND_DEVELOPER:
                    self._second_developer = event.timestamp
                if event.type == Event.Type.UNASSIGNED_2ND_DEVELOPER:
                    if self._second_developer:
                        yield Timeline(
                            self.main.issue_data.issue,
                            self._second_developer,
                            event.timestamp,
                            self.main.filter_display_name,
                            '',
                            Timeline.TYPE_ASSIGNED_2ND_DEVELOPER
                        )
                        self._second_developer = None

    class Assignee(ActionState):
        _assignee: datetime = None

        def process_action(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action) -> None:
            if action.field == 'assignee':
                if action.toString == self.main.filter_display_name:
                    self.main.event_queue.append(Event(item.created, Event.Type.ASSIGNED))
                if action.fromString == self.main.filter_display_name:
                    self.main.event_queue.append(Event(item.created, Event.Type.UNASSIGNED))

        def process_events(self) -> Iterator[Timeline]:
            for event in self.main.event_queue:
                if event.type == Event.Type.ASSIGNED:
                    self._assignee = event.timestamp
                if event.type == Event.Type.UNASSIGNED:
                    if self._assignee:
                        yield Timeline(
                            self.main.issue_data.issue,
                            self._assignee,
                            event.timestamp,
                            self.main.filter_display_name,
                            '',
                            Timeline.TYPE_ASSIGNED
                        )
                        self._assignee = None
                if event.type == Event.Type.TO_IN_PROGRESS:
                    if self._assignee:
                        yield Timeline(
                            self.main.issue_data.issue,
                            self._assignee,
                            event.timestamp,
                            self.main.filter_display_name,
                            '',
                            Timeline.TYPE_ASSIGNED
                        )
                        self._assignee = None


    class Progress(ActionState):
        _in_progress: datetime = None

        def process_action(self, item: ComputeTicketHistory.Response.Item,
                           action: ComputeTicketHistory.Response.Item.Action) -> None:
            if action.field == 'status':
                if action.toString == 'In Progress':
                    self.main.event_queue.append(Event(item.created, Event.Type.TO_IN_PROGRESS))
                if action.fromString == 'In Progress':
                    self.main.event_queue.append(Event(item.created, Event.Type.NO_LONGER_IN_PROGRESS))

        def process_events(self) -> Iterator[Timeline]:
            for event in self.main.event_queue:
                if event.type == Event.Type.TO_IN_PROGRESS:


            yield Timeline(self.issue_data.issue, self._in_progress, item.created, self.filter_display_name, '',
                           Timeline.TYPE_IN_PROGESS)
            self._in_progress = None
        if action.toString == 'In Progress' and not self._in_progress:
            # TODO make dry
            if self._assignee:
                yield Timeline(self.issue_data.issue, self._assignee, item.created, self.filter_display_name, '',
                               Timeline.TYPE_ASSIGNED)
                self._assignee = None
            if self._second_developer:
                yield Timeline(self.issue_data.issue, self._second_developer, item.created,
                               self.filter_display_name, '',
                               Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                self._second_developer = None
            self._in_progress = item.created

    class CalculateTimelines(Iterable[Timeline]):
        _in_progress: datetime = None
        _last_created: datetime = None
        ACTION_STATES = (SecondDeveloper, Assignee)
        event_queue: list[Event]

        def __init__(self, issue_data: IssueData, filter_display_name: str) -> None:
            self.issue_data = issue_data
            self.filter_display_name = filter_display_name
            self._action_states = (cls(self) for cls in self.ACTION_STATES)

        def __iter__(self) -> Iterator[Timeline]:
            history = asdataclass(ComputeTicketHistory.Response, self.issue_data.history)
            items = sorted(history.items, key=lambda item: item.created)
            self.event_queue = []
            for item in items:
                self._last_created = item.created
                for action in item.actions:
                    action: ComputeTicketHistory.Response.Item.Action
                    for action_state in self._action_states:
                        timeline = action_state.process_action(item, action)
                        if timeline:
                            yield timeline
            if self._last_created:
                if self._second_developer:
                    yield Timeline(self.issue_data.issue, self._second_developer, self._last_created, self.filter_display_name,
                                   '', Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                if self._assignee:
                    yield Timeline(self.issue_data.issue, self._assignee, self._last_created, self.filter_display_name, '',
                                   Timeline.TYPE_ASSIGNED)
                if self._in_progress:
                    yield Timeline(self.issue_data.issue, self._in_progress, self._last_created, self.filter_display_name, '',
                                   Timeline.TYPE_IN_PROGESS)
    return iter(CalculateTimelines(issue_data, filter_display_name))
