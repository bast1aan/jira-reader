from dataclasses import dataclass
from typing import Mapping

from bast1aan.jira_reader.async_executor import HttpAdapter, JSON



class TestHttpAdapter(HttpAdapter):
    @dataclass(frozen=True)
    class Request:
        url: str
        headers: tuple[tuple[str, str], ...]
        auth: HttpAdapter.Auth | None

    RequestResult = Mapping[Request, tuple[int, JSON]]

    request_result: RequestResult

    calls: list[tuple[Request, tuple[int, JSON]]]

    def __init__(self, request_result: RequestResult):
        super().__init__()
        self.request_result = request_result
        self.calls = []

    async def get(self, url: str, headers: dict[str, str], auth: HttpAdapter.Auth | None = None) -> tuple[int, JSON]:
        req = self.Request(url, tuple(headers.items()), auth)
        result = self.request_result.get(req)
        if not result:
            result = 404, {'result': 'NotFound'}
        self.calls.append((req, result))
        return result
