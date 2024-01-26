import abc
from typing import TypeVar, Protocol, Generic, ClassVar

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

