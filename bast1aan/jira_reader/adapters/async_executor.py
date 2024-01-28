import json
from typing import ClassVar

import aiohttp

from bast1aan.jira_reader.async_executor import HttpAdapter, JSON


class AioHttpAdapter(HttpAdapter):
    unix_socket: ClassVar[str] = ''  # to overwrite to connect over unix socket when testing

    @property
    def _connector(self) -> aiohttp.BaseConnector | None:
        if self.unix_socket:
            return aiohttp.UnixConnector(self.unix_socket)

    async def get(self, url: str, headers: dict[str, str], auth: HttpAdapter.Auth | None = None) -> tuple[int, JSON]:
        if auth.login:
            auth = aiohttp.BasicAuth(login=auth.login, password=auth.password)
        else:
            auth = None
        async with aiohttp.ClientSession(auth=auth, connector=self._connector) as session, \
            session.get(url=url, headers=headers) as response:
            return response.status, json.loads(await response.read())

