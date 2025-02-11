from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timedelta
from enum import Enum, auto as a
from itertools import chain
from typing import Mapping, TypeVar, Iterator, Iterable, ClassVar, Callable, Literal, Sequence, Final

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
        issue_id: int
        project_id: int
        summary: str
        created: datetime
        created_by: str

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
            },
            'created': into(Response).created
        },
        "id": into(Response).issue_id,
        "fields": {
            "project": {
                "id": into(Response).project_id,
            },
            "summary": into(Response).summary,
            "reporter": {
                "displayName": into(Response).created_by
            }
        },
    }, convert_null_to_empty_value=True)

def calculate_timelines(issue_data: IssueData, filter_display_name: str, from_:datetime|None=None) -> Iterator[Timeline]:
    class State(Enum):
        IN_PROGRESS=a()
        SECOND_DEVELOPER=a()
        ASSIGNED=a()
        WRITING_COMMENT=a()
        CREATING_TICKET=a()

    StateChange = Literal[True] | Literal[False]
    to: Final[StateChange] = True
    no_longer: Final[StateChange] = False

    def assume_current_timezone_for_naive_datetime(input: datetime) -> datetime:
        # this could be wrong because of daylight saving time
        return input.replace(tzinfo=datetime.now().astimezone().tzinfo)

    def convert_comment_to_items_with_actions(comment: ComputeTicketHistory.Response.Comment) -> Iterable[ComputeTicketHistory.Response.Item]:
        return ComputeTicketHistory.Response.Item(
            byEmailAddress=comment.byEmailAddress,
            byDisplayName=comment.byDisplayName,
            created=assume_current_timezone_for_naive_datetime(comment.created),
            actions=[
                ComputeTicketHistory.Response.Item.Action(
                    field='comment',
                    fromString='',
                    toString=comment.byDisplayName
                ),
            ]
        ), ComputeTicketHistory.Response.Item(
            byEmailAddress=comment.byEmailAddress,
            byDisplayName=comment.byDisplayName,
            created=assume_current_timezone_for_naive_datetime(comment.created) + timedelta(minutes=15),
            actions=[
                ComputeTicketHistory.Response.Item.Action(
                    field='comment',
                    fromString=comment.byDisplayName,
                    toString=''
                ),
            ]
        )

    def create_creating_items(created: datetime, created_by: str) -> Iterable[ComputeTicketHistory.Response.Item]:
        return ComputeTicketHistory.Response.Item(
            byEmailAddress='',
            byDisplayName=created_by,
            created=assume_current_timezone_for_naive_datetime(created),
            actions=[
                ComputeTicketHistory.Response.Item.Action(
                    field='creating_ticket',
                    fromString='',
                    toString=created_by
                ),
            ]
        ), ComputeTicketHistory.Response.Item(
            byEmailAddress='',
            byDisplayName=created_by,
            created=assume_current_timezone_for_naive_datetime(created) + timedelta(minutes=15),
            actions=[
                ComputeTicketHistory.Response.Item.Action(
                    field='creating_ticket',
                    fromString=created_by,
                    toString='',
                ),
            ]
        )

    class Processor:
        state_observers: ClassVar[Mapping[tuple[StateChange, State]: Callable]]
        field_name: ClassVar[str]
        def __init__(self, main: CalculateTimelines):
            self.main = main
        def process(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action):
            ...
        def get_state_observers(self) -> Mapping[tuple[StateChange, State]: Callable]:
            def create_wrapper(func):
                # add self to classvar defined method references
                return lambda *args, **kwargs: func(self, *args, **kwargs)
            return {
                st: create_wrapper(func)
                for st, func in self.state_observers.items()
            }

    class SimpleProcessor(Processor):
        state: ClassVar[State]
        timeline_type: ClassVar[str]
        _state_added: datetime | None = None
        def process(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action):
            if action.toString == self.main.filter_display_name:
                self.main.change_state(to, self.state, item.created)
            if action.fromString == self.main.filter_display_name:
                self.main.change_state(no_longer, self.state, item.created)

        def on_add_state(self, timestamp: datetime) -> Iterator[Timeline]:
            if State.IN_PROGRESS not in self.main.states:
                self._state_added = timestamp
            yield from ()

        def on_remove_state(self, timestamp: datetime) -> Iterator[Timeline]:
            if self._state_added:
                yield Timeline(
                    self.main.issue_data.issue,
                    self._state_added,
                    timestamp,
                    self.main.filter_display_name,
                    '',
                    self.timeline_type,
                    self.main.issue_data.summary,
                )
                self._state_added = None

        def to_in_progress(self, timestamp: datetime) -> Iterator[Timeline]:
            # end 'assigned' timeline if tickets moves in progress.
            if self.state in self.main.states:
                yield from self.on_remove_state(timestamp)

        def no_longer_in_progress(self, timestamp: datetime) -> Iterator[Timeline]:
            # restart timeline for original state
            if self.state in self.main.states:
                self._state_added = timestamp
            yield from ()

        def get_state_observers(self) -> Mapping[tuple[StateChange, State]: Callable]:
            return {
                (to, self.state): self.on_add_state,
                (no_longer, self.state): self.on_remove_state,
                (to, State.IN_PROGRESS): self.to_in_progress,
                (no_longer, State.IN_PROGRESS): self.no_longer_in_progress,
            }

    class SecondDeveloperProcessor(SimpleProcessor):
        field_name = '2nd Developer'
        state = State.SECOND_DEVELOPER
        timeline_type = Timeline.TYPE_ASSIGNED_2ND_DEVELOPER

    class AssigneeProcessor(SimpleProcessor):
        field_name = 'assignee'
        state = State.ASSIGNED
        timeline_type = Timeline.TYPE_ASSIGNED

    class WritingCommentProcessor(SimpleProcessor):
        field_name = 'comment'
        state = State.WRITING_COMMENT
        timeline_type = Timeline.TYPE_WRITING_COMMENT

    class CreatingTicketProcessor(SimpleProcessor):
        field_name = 'creating_ticket'
        state = State.CREATING_TICKET
        timeline_type = Timeline.TYPE_CREATING_TICKET

    class StatusProcessor(Processor):
        field_name = 'status'
        _state_added: datetime | None = None

        def process(self, item: ComputeTicketHistory.Response.Item, action: ComputeTicketHistory.Response.Item.Action):
            if action.toString == 'In Progress':
                self.main.change_state(to, State.IN_PROGRESS, item.created)
            if action.fromString == 'In Progress':
                self.main.change_state(no_longer, State.IN_PROGRESS, item.created)

        def _assigned_or_2nddev(self) -> bool:
            return State.ASSIGNED in self.main.states or State.SECOND_DEVELOPER in self.main.states

        def on_add_state(self, timestamp: datetime) -> Iterator[Timeline]:
            if self._assigned_or_2nddev():
                self._state_added = timestamp
            yield from ()

        def on_remove_state(self, timestamp: datetime) -> Iterator[Timeline]:
            if self._state_added:
                yield Timeline(
                    self.main.issue_data.issue,
                    self._state_added,
                    timestamp,
                    self.main.filter_display_name,
                    '',
                    Timeline.TYPE_IN_PROGESS,
                    self.main.issue_data.summary,
                )
                self._state_added = None

        def on_assigned(self, timestamp: datetime) -> Iterator[Timeline]:
            if State.IN_PROGRESS in self.main.states and not self._state_added:
                self._state_added = timestamp
            yield from ()

        def on_unassigned(self, timestamp: datetime) -> Iterator[Timeline]:
            if not self._assigned_or_2nddev():
                yield from self.on_remove_state(timestamp)

        state_observers = {
            (to, State.IN_PROGRESS): on_add_state,
            (no_longer, State.IN_PROGRESS): on_remove_state,
            (to, State.ASSIGNED): on_assigned,
            (to, State.SECOND_DEVELOPER): on_assigned,
            (no_longer, State.ASSIGNED): on_unassigned,
            (no_longer, State.SECOND_DEVELOPER): on_unassigned,
        }

    class CalculateTimelines(Iterable[Timeline]):
        processors = (
            CreatingTicketProcessor,
            SecondDeveloperProcessor,
            AssigneeProcessor,
            StatusProcessor,
            WritingCommentProcessor,
        )
        _states: dict[State, datetime]
        _state_changes: list[tuple[StateChange, State, datetime]]

        def change_state(self, statechange: StateChange, state: State, timestamp: datetime) -> None:
            if statechange is to:
                self._states[state] = timestamp
            if statechange is no_longer:
                if state not in self._states:
                    return  # should not happen
                self._states.pop(state)
            self._state_changes.append((statechange, state, timestamp))

        @property
        def states(self) -> Mapping[State, datetime]:
            return self._states

        def __init__(self, issue_data: IssueData, filter_display_name: str) -> None:
            self.issue_data = issue_data
            self.filter_display_name = filter_display_name
            self._states = {}
            self._processors: Sequence[Processor] = tuple(cls(self) for cls in self.processors)
            self._state_changes = []

        def _process_state_changes(self) -> Iterator[Timeline]:

            all_state_observers = defaultdict(list)
            for processor in self._processors:
                for state_change_state, method in processor.get_state_observers().items():
                    all_state_observers[state_change_state].append(method)

            for state_change, state, timestamp in self._state_changes:
                 for method in all_state_observers.get((state_change, state)):
                    yield from method(timestamp)
            self._state_changes.clear()
            #
            # for processor in self._processors:
            #     for state_change_state, method in processor.get_state_observers():
            #         method

        def __iter__(self) -> Iterator[Timeline]:

            history = asdataclass(
                ComputeTicketHistory.Response,
                {
                    **self.issue_data.history,
                    'issue_id': self.issue_data.issue_id,
                    'project_id': self.issue_data.project_id,
                    'summary': self.issue_data.summary,
                    'created': self.issue_data.created,
                    'created_by': self.issue_data.created_by
                }
            )

            creating_items = create_creating_items(created=history.created, created_by=history.created_by)

            comment_items_iterators = (convert_comment_to_items_with_actions(comment) for comment in history.comments)

            items = sorted(
                chain(
                    creating_items,
                    history.items,
                    *comment_items_iterators,
                ),
                key=lambda item: item.created
            )
            last_created = None
            for item in items:
                last_created = item.created
                for action in item.actions:
                    action: ComputeTicketHistory.Response.Item.Action
                    for processor in self._processors:
                        if action.field == processor.field_name:
                            processor.process(item, action)
                    yield from self._process_state_changes()
                    #       yield from
                    # if action.field == '2nd Developer':
                    #     if self._second_developer:
                    #         yield Timeline(self.issue_data.issue, self._second_developer, item.created, self.filter_display_name,
                    #                        '', Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                    #         self._second_developer = None
                    #     if action.toString == self.filter_display_name:
                    #         self._second_developer = item.created
                    # if action.field == 'assignee':
                    #     if self._assignee:
                    #         yield Timeline(self.issue_data.issue, self._assignee, item.created, self.filter_display_name, '',
                    #                        Timeline.TYPE_ASSIGNED)
                    #         self._assignee = None
                    #     if action.toString == self.filter_display_name:
                    #         self._assignee = item.created
                    # if action.field == 'status' and (self._second_developer or self._assignee):
                    #     if action.fromString == 'In Progress' and self._in_progress:
                    #         yield Timeline(self.issue_data.issue, self._in_progress, item.created, self.filter_display_name, '',
                    #                        Timeline.TYPE_IN_PROGESS)
                    #         self._in_progress = None
                    #     if action.toString == 'In Progress' and not self._in_progress:
                    #         # TODO make dry
                    #         if self._assignee:
                    #             yield Timeline(self.issue_data.issue, self._assignee, item.created, self.filter_display_name, '',
                    #                            Timeline.TYPE_ASSIGNED)
                    #             self._assignee = None
                    #         if self._second_developer:
                    #             yield Timeline(self.issue_data.issue, self._second_developer, item.created,
                    #                            self.filter_display_name, '',
                    #                            Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                    #             self._second_developer = None
                    #         self._in_progress = item.created
            if last_created:
                for state in tuple(self.states.keys()):
                    self.change_state(no_longer, state, last_created)
                yield from self._process_state_changes()

                # if self._second_developer:
                #     yield Timeline(self.issue_data.issue, self._second_developer, self._last_created, self.filter_display_name,
                #                    '', Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                # if self._assignee:
                #     yield Timeline(self.issue_data.issue, self._assignee, self._last_created, self.filter_display_name, '',
                #                    Timeline.TYPE_ASSIGNED)
                # if self._in_progress:
                #     yield Timeline(self.issue_data.issue, self._in_progress, self._last_created, self.filter_display_name, '',
                #                    Timeline.TYPE_IN_PROGESS)
    calculate_timelines_iterator = iter(CalculateTimelines(issue_data, filter_display_name))
    if from_:
        calculate_timelines_iterator = limit_earliest_date(calculate_timelines_iterator, from_=from_)
    return calculate_timelines_iterator

def limit_earliest_date(timeline: Iterator[Timeline], from_: datetime) -> Iterator[Timeline]:
    for item in timeline:
        if item.end >= from_:
            if item.start < from_:
                yield replace(item, start=from_)
            else:
                yield item
