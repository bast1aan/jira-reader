from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, TypeVar, Generic, Protocol

from .json_mapper import JsonMapper, into

InputType = TypeVar('InputType')
ResponseType = TypeVar('ResponseType')

class Mapper(Protocol[ResponseType]):
    def __call__(self, input: object) -> ResponseType:
        raise NotImplementedError

class Action(Generic[ResponseType], abc.ABC):
    URL: ClassVar[str]
    mapper: ClassVar[Mapper[ResponseType] | None] = None

    def get_response(self, input: object) -> ResponseType:
        if self.mapper:
            return self.mapper(input)
        else:
            raise NotImplementedError


@dataclass
class RequestTicketHistory(Action["RequestTicketHistory.Response"]):
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

