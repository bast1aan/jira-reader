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

@dataclass
class RequestTicketHistory(JiraAction["RequestTicketHistory.Response"]):
    @dataclass
    class Response:
        @dataclass
        class Item:
            @dataclass
            class Action:
                field: str
                toString: str
                fromString: str | None

            byEmailAddress: str | None
            byDisplayName: str
            created: datetime
            actions: list[RequestTicketHistory.Response.Item.Action]

        items: list[Item]

    URL = '/rest/api/3/issue/{issue}?expand=renderedFields,changelog'
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
        }
    })
    issue: str
