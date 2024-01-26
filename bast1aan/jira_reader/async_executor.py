from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from bast1aan.jira_reader.reader import Action

T = TypeVar('T')

JSON = dict | list | str

class HttpAdapter(ABC):
    @dataclass(frozen=True)
    class Auth:
        login: str
        password: str
    @abstractmethod
    async def get(self, url: str, headers: dict[str, str], auth: Auth | None = None) -> tuple[int, JSON]:
        """ Performs a GET http request, returns status code and json. """


@dataclass
class Executor:
    adapter: HttpAdapter

    async def __call__(self, action: Action[T]) -> T:
        """ Raises: ExecutorException """
        url = action.HOST + action.url
        auth = None
        if action.AUTH_LOGIN and action.AUTH_PASSWORD:
            auth = HttpAdapter.Auth(login=action.AUTH_LOGIN, password=action.AUTH_PASSWORD)
        status, json = await self.adapter.get(url, {'Accept': 'application/json'}, auth=auth)
        if status // 100 != 2:
            raise ExecutorException(status, json)
        return action.get_response(json)


class ExecutorException(Exception): pass
