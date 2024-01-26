import abc
from typing import TypeVar, Protocol, Generic, ClassVar, Mapping

ResponseType = TypeVar('ResponseType')

class Mapper(Protocol[ResponseType]):
    def __call__(self, input: object) -> ResponseType:
        raise NotImplementedError

class Action(Generic[ResponseType], abc.ABC):
    HOST: ClassVar[str]
    AUTH_LOGIN: ClassVar[str] = ''
    AUTH_PASSWORD: ClassVar[str] = ''
    URL: ClassVar[str]
    mapper: ClassVar[Mapper[ResponseType] | None] = None
    url_args: Mapping[str, str]

    @property
    def url(self) -> str:
        return self.URL.format(**self.url_args)

    def get_response(self, input: object) -> ResponseType:
        if self.mapper:
            return self.mapper(input)
        else:
            raise NotImplementedError

