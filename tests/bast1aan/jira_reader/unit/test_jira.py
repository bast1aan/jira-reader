import os
import importlib.util
import json
import types
import unittest

from bast1aan.jira_reader import async_executor
from bast1aan.jira_reader.jira import RequestTicketHistory
from tests.bast1aan.jira_reader.adapters.async_executor import TestHttpAdapter


class TestRequestTicketHistory(unittest.IsolatedAsyncioTestCase):

    JIRA_HOST = 'https://jira-host'
    JIRA_EMAIL = 'user@example.com'
    JIRA_API_TOKEN = 'jira_api_token'

    def test_action(self):
        with open('test_jira/test_request_ticket_history/test_input.json', 'r') as f:
            input = json.load(f)
        expected = get_module_from_file('test_jira/test_request_ticket_history/test_expected.py')

        action = RequestTicketHistory(issue='ABC-123')

        result = action.get_response(input)

        self.assertEqual(expected.expected, result)

    async def test_executor(self):
        with open('test_jira/test_request_ticket_history/test_input.json', 'r') as f:
            input = json.load(f)
        expected = get_module_from_file('test_jira/test_request_ticket_history/test_expected.py')

        adapter = TestHttpAdapter(request_result={
            TestHttpAdapter.Request(
                url='https://jira-host/rest/api/3/issue/ABC-123?expand=renderedFields,changelog',
                headers=(('Accept', 'application/json'),),
                auth=TestHttpAdapter.Auth(login=self.JIRA_EMAIL, password=self.JIRA_API_TOKEN),
            ) : (200, input)}
        )

        execute = async_executor.Executor(adapter)
        action = RequestTicketHistory(issue='ABC-123')

        result = await execute(action)
        self.assertEqual(expected.expected, result)


def get_module_from_file(path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
