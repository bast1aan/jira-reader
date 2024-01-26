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
class RequestTicketHistoryResponse:
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
        actions: list[RequestTicketHistoryResponse.Item.Action]
    items: list[Item]


@dataclass
class RequestTicketHistory(Action[RequestTicketHistoryResponse]):
    URL = '/rest/api/3/issue/{issue}?expand=renderedFields,changelog'
    mapper = JsonMapper({
        'changelog': {
            'histories': [{
                'author': {
                    'emailAddress': into(RequestTicketHistoryResponse.Item).byEmailAddress,
                    'displayName': into(RequestTicketHistoryResponse.Item).byDisplayName,
                },
                'items': [{
                   'field': into(RequestTicketHistoryResponse.Item.Action).field,
                   'toString': into(RequestTicketHistoryResponse.Item.Action).toString,
                   'fromString': into(RequestTicketHistoryResponse.Item.Action).fromString,
                }, into(RequestTicketHistoryResponse.Item).actions],
                'created': into(RequestTicketHistoryResponse.Item).created,
            }, into(RequestTicketHistoryResponse).items],
        }
    })
    issue: str

