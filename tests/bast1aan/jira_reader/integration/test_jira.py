import asyncio
import json
import os
import unittest
import socket

import aiohttp.web

import tempfile

from tests.bast1aan.jira_reader.util import get_module_from_file, scriptdir


class TestRequestTicketHistory(unittest.IsolatedAsyncioTestCase):
    requests: list[aiohttp.web.Request]
    app_task: asyncio.Task

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.requests = []

        async def jira(request: aiohttp.web.Request) -> aiohttp.web.Response:
            self.requests.append(request)
            return aiohttp.web.Response(
                body=open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'r').read(),
                headers={'content-type': 'application/json'},
            )

        self.tmpdir = tempfile.mkdtemp()
        self.socketpath = os.path.join(self.tmpdir, 'socket')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socketpath)

        jira_app = aiohttp.web.Application()
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-123', jira)])
        self.app_task = asyncio.create_task(aiohttp.web._run_app(jira_app, sock=self.sock))#  host='localhost', port=51391))

    async def asyncTearDown(self):
        self.app_task.cancel()
        os.remove(self.socketpath)
        os.rmdir(self.tmpdir)
        await super().asyncTearDown()

    async def test_test(self):
        expected = open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'rb').read()

        async with aiohttp.ClientSession(connector=aiohttp.UnixConnector(self.socketpath)) as client, \
            client.get('https://jira-host/rest/api/3/issue/ABC-123?expand=renderedFields,changelog',
                       headers={'Accept': 'application/json'}) as response:
            result = await response.read()
            self.assertEqual(json.loads(result), json.loads(expected))
