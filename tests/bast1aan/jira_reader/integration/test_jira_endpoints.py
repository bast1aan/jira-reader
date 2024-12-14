import asyncio
import json
import os
import unittest
from contextlib import asynccontextmanager
from datetime import datetime

import aiohttp.web

import bast1aan.jira_reader.adapters.async_executor
import bast1aan.jira_reader.rest_api
from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.sqlstorage import Base
from bast1aan.jira_reader.entities import Request

from tests.bast1aan.jira_reader.adapters.setup_flask import setup_flask
from tests.bast1aan.jira_reader.adapters.sqlstorage import TestSQLStorage
from tests.bast1aan.jira_reader.integration.base import AsyncHttpRequestMixin
from tests.bast1aan.jira_reader.util import scriptdir, exists


class JiraTestCase(AsyncHttpRequestMixin, unittest.IsolatedAsyncioTestCase):
    maxDiff = None
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

        jira_app = aiohttp.web.Application()
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-123', jira)])
        self.app_task = asyncio.create_task(aiohttp.web._run_app(jira_app, sock=self.sock))
        await exists(self.socketpath)
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = self.socketpath
        self.storage = TestSQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()
        await self.storage.clean_up()
        bast1aan.jira_reader.rest_api._storage = self.storage

    async def asyncTearDown(self):
        self.app_task.cancel()
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
            async with self.get('http://flask/api/jira/compute-history/ABC-123', flask_sock) as response:
                result = await response.read()
                self.assertEqual(2, response.status // 100)
                self.assertEqual(json.loads(expected), json.loads(result))
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)

    async def test_jira_request_saved_to_db(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_expected.json'), 'rb') as f:
            expected = f.read()

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.get('http://flask/api/jira/compute-history/ABC-123', flask_sock) as response:
                result = await response.read()
                self.assertEqual(2, response.status // 100)
                self.assertEqual(json.loads(expected), json.loads(result))
                latest_request = await self.storage.get_latest_request('ABC-123')
                self.assertIsNotNone(latest_request)
                self.assertEqual('ABC-123', latest_request.issue)
                self.assertEqual(json.loads(expected), latest_request.result)
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)

class JiraFetchDataTestCase(AsyncHttpRequestMixin, unittest.IsolatedAsyncioTestCase):
    maxDiff = None
    requests: list[aiohttp.web.Request]
    app_task: asyncio.Task

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.requests = []

        async def jira(request: aiohttp.web.Request) -> aiohttp.web.Response:
            self.requests.append(request)
            with open(scriptdir('test_jira/test_fetch_ticket_data/testdata.json'), 'r') as f:
                return aiohttp.web.Response(
                    body=f.read(),
                    headers={'content-type': 'application/json'},
                )

        async def jira_404(request: aiohttp.web.Request) -> aiohttp.web.Response:
            self.requests.append(request)
            return aiohttp.web.Response(
                status=404,
                body=b'{"errorMessages": ["Issue does not exist or you do not have permission to see it."], "errors": {}}',
                headers={'content-type': 'application/json'},
            )

        jira_app = aiohttp.web.Application()
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-123', jira)])
        jira_app.add_routes([aiohttp.web.get('/rest/api/3/issue/ABC-404', jira_404)])
        self.app_task = asyncio.create_task(aiohttp.web._run_app(jira_app, sock=self.sock))
        await exists(self.socketpath)
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = self.socketpath
        self.storage = TestSQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()
        await self.storage.clean_up()
        bast1aan.jira_reader.rest_api._storage = self.storage

    async def asyncTearDown(self):
        self.app_task.cancel()
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = ''
        await super().asyncTearDown()

    async def test_fetch_data_get(self):
        with open(scriptdir('test_jira/test_fetch_ticket_data/testdata.json'), 'rb') as f:
            expected = f.read()
        await self.storage.save_request(Request(issue='ABC-123', result=json.loads(expected)))

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.get('http://flask/api/jira/fetch-data/ABC-123', flask_sock) as response:
                result = await response.read()
                self.assertEqual(2, response.status // 100)
                self.assertEqual(json.loads(expected), json.loads(result))

            self.assertEqual(len(self.requests), 0, 'No request should\'ve been executed')
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)

    async def test_fetch_post(self):
        self.assertEqual(len(self.requests), 0)
        self.assertIsNone(await self.storage.get_latest_request('ABC-123'))

        with open(scriptdir('test_jira/test_fetch_ticket_data/testdata.json'), 'rb') as f:
            expected = f.read()

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.post('http://flask/api/jira/fetch-data/ABC-123', flask_sock) as response:
                result = await response.read()
                self.assertEqual(201, response.status)
                self.assertEqual(json.loads(expected), json.loads(result))

            latest_request = await self.storage.get_latest_request('ABC-123')
            self.assertIsNotNone(latest_request)
            self.assertEqual('ABC-123', latest_request.issue)
            self.assertEqual(json.loads(expected), latest_request.result)

            self.assertEqual(len(self.requests), 1, 'Data should have been requested')
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)

    async def test_jira_gives_404_does_not_crash(self):
        self.assertIsNone(await self.storage.get_latest_request('ABC-123'))

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.post('http://flask/api/jira/fetch-data/ABC-404', flask_sock) as response:
                result = await response.read()
                self.assertEqual(404, response.status)
                self.assertEqual(
                    {
                        'errorMessages': ['Issue does not exist or you do not have permission to see it.'],
                        'errors': {}
                    },
                    json.loads(result)
                )
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)


class TimelineTestCase(AsyncHttpRequestMixin, unittest.IsolatedAsyncioTestCase):
    maxDiff = None

    async def setup_issue_data(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_expected.json'), 'rb') as f:
            input = f.read()
        await self.storage.save_issue_data(entities.IssueData(
            issue='XYZ-987',
            history=json.loads(input),
            computed=datetime.now(),
            issue_id=123,
            project_id=456,
            summary='XYZ Summary'
        ))

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.storage = TestSQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()
        await self.storage.clean_up()
        await self.setup_issue_data()
        bast1aan.jira_reader.rest_api._storage = self.storage

    async def asyncTearDown(self):
        bast1aan.jira_reader.adapters.async_executor.AioHttpAdapter.unix_socket = ''
        await super().asyncTearDown()

    async def test_timeline(self):
        with open(scriptdir('test_jira/timeline/expected.json'), 'rb') as f:
            expected = f.read()

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.get('http://flask/api/jira/timeline/Bastiaan%20Welmers', flask_sock) as response:
                result = await response.read()
                self.assertEqual(2, response.status // 100)
                self.assertEqual(json.loads(expected), json.loads(result))
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)

    async def test_timeline_ical(self):
        with open(scriptdir('test_jira/timeline/expected.ics'), 'rb') as f:
            expected = f.read()

        flask_sock = os.path.join(self.tmpdir, 'flask.sock')

        flask_task = setup_flask(flask_sock)
        await exists(flask_sock)

        try:
            async with self.get('http://flask/api/jira/timeline-ical/Bastiaan%20Welmers', flask_sock) as response:
                response: aiohttp.ClientResponse
                self.assertEqual(2, response.status // 100)
                self.assertEqual(
                    "text/calendar; charset=utf-8",
                    response.headers['content-type']
                )
                self.assertEqual(
                    'attachment; filename="jira-reader Bastiaan Welmers.ics"',
                    response.headers['content-disposition']
                )
                body = await response.read()
                self.assertEqual(expected, body)
        finally:
            flask_task.cancel()
            os.unlink(flask_sock)
