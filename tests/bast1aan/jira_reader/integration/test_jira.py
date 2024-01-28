import asyncio
import json
import os
import unittest
import socket
from contextlib import asynccontextmanager

import aiohttp.web

import tempfile

import bast1aan.jira_reader.adapters.async_executor

from tests.bast1aan.jira_reader.adapters.setup_flask import setup_flask
from tests.bast1aan.jira_reader.util import scriptdir, exists


class TestRequestTicketHistory(unittest.IsolatedAsyncioTestCase):
    requests: list[aiohttp.web.Request]
    app_task: asyncio.Task

    def _setup_socket(self):
        self.tmpdir = tempfile.mkdtemp()
        self.socketpath = os.path.join(self.tmpdir, 'socket')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socketpath)

    def _tear_down_socket(self):
        os.remove(self.socketpath)
        os.rmdir(self.tmpdir)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.requests = []

        self._setup_socket()

        async def jira(request: aiohttp.web.Request) -> aiohttp.web.Response:
            self.requests.append(request)
            return aiohttp.web.Response(
                body=open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'r').read(),
                headers={'content-type': 'application/json'},
            )

        jira_app = aiohttp.web.Application()
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-123', jira)])
        self.app_task = asyncio.create_task(aiohttp.web._run_app(jira_app, sock=self.sock))
        await exists(self.socketpath)
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = self.socketpath

    async def asyncTearDown(self):
        self.app_task.cancel()
        self._tear_down_socket()
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = ''
        await super().asyncTearDown()

    @asynccontextmanager
    async def get(self, url: str, socketpath: str = '') -> aiohttp.ClientResponse:
        async with aiohttp.ClientSession(connector=aiohttp.UnixConnector(socketpath or self.socketpath)) as client, \
                client.get(url, headers={'Accept': 'application/json'}) as response:
            yield response

    async def test_test(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'rb') as f:
            expected = f.read()
        async with self.get('https://jira-host/rest/api/3/issue/ABC-123?expand=renderedFields,changelog') as response:
            result = await response.read()
            self.assertEqual(json.loads(result), json.loads(expected))

    async def test_jira(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_expected.json'), 'rb') as f:
            expected = f.read()

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.get('http://flask/api/jira/request-ticket-history/ABC-123', flask_sock) as response:
                result = await response.read()
                self.assertEqual(2, response.status // 100)
                self.assertEqual(json.loads(expected), json.loads(result))
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)
