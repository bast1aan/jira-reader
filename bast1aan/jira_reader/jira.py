from __future__ import annotations
from dataclasses import dataclass, is_dataclass, fields, Field
from datetime import datetime
from functools import cached_property
from typing import ClassVar, TypeVar, Generic, Protocol, Any, Callable, Mapping

from .json_mapper import JsonMapper, into

InputType = TypeVar('InputType')
ResponseType = TypeVar('ResponseType')

class Mapper(Protocol[ResponseType]):
    def __call__(self, input: object) -> ResponseType:
        raise NotImplementedError

# @dataclass
# class ResponseParam:
#     cls: ResponseType
#     param: str
#     value: Any = None
#     value_factory: Callable = None
#
#
# Mapping = dict[str, ResponseParam] | list[ResponseParam]
#
# class InputMapper(Generic[ResponseType]):
#     def __init__(self, mapping: Mapping | dict[str, Mapping] | list[str, Mapping]):
#         self.mapping = mapping
#     def __call__(self, input: object) -> ResponseType:
#         ...


# class ResponseBuilder(Protocol[ResponseType]):
#     def __call__(self, response: ResponseType, value: Any) -> ResponseType:
#        ...

class Action(Generic[ResponseType]):
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

# changelog {
# 	histories {
# 		items: list[
# 		{field, fromString, toString}
# 		]
# 		author: {
# 		emailAddress,
# 		displayName,
# 		}
# 		created: datetime
# 	}
# }
