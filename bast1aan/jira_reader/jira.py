from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Mapping, TypeVar, Iterator

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
    second_developer: datetime = None
    assignee: datetime = None
    in_progress: datetime = None
    last_created = None

    history = asdataclass(ComputeTicketHistory.Response, issue_data.history)
    items = sorted(history.items, key=lambda item: item.created)

    for item in items:
        last_created = item.created
        for action in item.actions:
            action: ComputeTicketHistory.Response.Item.Action
            if action.field == '2nd Developer':
                if second_developer:
                    yield Timeline(issue_data.issue, second_developer, item.created, filter_display_name, '', Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
                    second_developer = None
                if action.toString == filter_display_name:
                    second_developer = item.created
            if action.field == 'assignee':
                if assignee:
                    yield Timeline(issue_data.issue, assignee, item.created, filter_display_name, '', Timeline.TYPE_ASSIGNED)
                    assignee = None
                if action.toString == filter_display_name:
                    assignee = item.created
            if action.field == 'status' and (second_developer or assignee):
                if action.fromString == 'In Progress' and in_progress:
                    yield Timeline(issue_data.issue, in_progress, item.created, filter_display_name, '',
                                   Timeline.TYPE_IN_PROGESS)
                    in_progress = None
                if action.toString == 'In Progress':
                    in_progress = item.created
    if last_created:
        if second_developer:
            yield Timeline(issue_data.issue, second_developer, last_created, filter_display_name, '', Timeline.TYPE_ASSIGNED_2ND_DEVELOPER)
        if assignee:
            yield Timeline(issue_data.issue, assignee, last_created, filter_display_name, '', Timeline.TYPE_ASSIGNED)
        if in_progress:
            yield Timeline(issue_data.issue, in_progress, last_created, filter_display_name, '', Timeline.TYPE_IN_PROGESS)
