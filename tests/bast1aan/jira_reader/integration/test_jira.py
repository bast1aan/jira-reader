import asyncio
import unittest
from typing import ClassVar

import aiohttp.web

class TestRequestTicketHistory(unittest.IsolatedAsyncioTestCase):
    requests: list[aiohttp.web.Request]
    app_task: asyncio.Task

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.requests = []

        async def jira(request: aiohttp.web.Request) -> aiohttp.web.Response:
            return aiohttp.web.Response(
                body=open('test_jira/test_request_ticket_history/test_input.json', 'r').read(),
                headers={'content-type': 'application/json'},
            )
        jira_app = aiohttp.web.Application()
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-123?expand=renderedFields,changelog', jira)])
        self.app_task = asyncio.create_task(aiohttp.web._run_app(jira_app, host='localhost', port=51391))

    async def test(self):
        async with aiohttp.ClientSession() as client, \
            client.get('http://localhost:51391/rest/api/3/issue/ABC-123?expand=renderedFields,changelog',
                       headers={'Accept': 'application/json'}) as response:
            result = await response.read()
            self.fail(result)

    async def asyncTearDown(self):
        self.app_task.cancel()
        await super().asyncTearDown()
