import os
import socket
import tempfile
from contextlib import asynccontextmanager
from typing import Literal, AsyncContextManager, Final, ParamSpec
from unittest import TestCase

import aiohttp

P = ParamSpec('P')

class AsyncHttpRequestMixin(TestCase):
    def __init__(self, *args: P.args, **kwargs: P.kwargs):
        super().__init__(*args, **kwargs)
        self.tmpdir: Final[str] = tempfile.mkdtemp()
        self.addCleanup(lambda: os.rmdir(self.tmpdir))

    def setUp(self) -> None:
        super().setUp()
        self.socketpath = os.path.join(self.tmpdir, 'socket')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socketpath)

    def tearDown(self) -> None:
        os.remove(self.socketpath)
        super().tearDown()

    @asynccontextmanager
    async def request(self, method: Literal['GET', 'POST'], url: str, socketpath: str = '') -> aiohttp.ClientResponse:
        async with aiohttp.ClientSession(connector=aiohttp.UnixConnector(socketpath or self.socketpath)) as client, \
                client.request(method, url, headers={'Accept': 'application/json'}) as response:
            yield response

    def get(self, url: str, socketpath: str = '') -> AsyncContextManager[aiohttp.ClientResponse]:
        return self.request('GET', url, socketpath)

    def post(self, url: str, socketpath: str = '') -> AsyncContextManager[aiohttp.ClientResponse]:
        return self.request('POST', url, socketpath)
