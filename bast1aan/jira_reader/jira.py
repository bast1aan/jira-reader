from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Mapping, TypeVar

from .json_mapper import JsonMapper, into
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
