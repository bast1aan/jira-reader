import json
import unittest
from datetime import datetime

from dateutil.tz import tzoffset

from bast1aan.jira_reader import async_executor, entities, json_mapper
from bast1aan.jira_reader.async_executor import ExecutorException
from bast1aan.jira_reader.jira import ComputeTicketHistory, RequestTicketData, calculate_timelines
from tests.bast1aan.jira_reader.adapters.async_executor import TestHttpAdapter
from tests.bast1aan.jira_reader.util import get_module_from_file, scriptdir


class TestRequestTicketHistory(unittest.TestCase):

    def test_action(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'r') as f:
            input = json.load(f)
        expected = get_module_from_file('test_jira/test_request_ticket_history/test_expected.py')

        action = ComputeTicketHistory()

        result = action.get_response(input)

        self.assertEqual(expected.expected, result)


class TestRequestTicketData(unittest.IsolatedAsyncioTestCase):

    JIRA_HOST = 'https://jira-host'
    JIRA_EMAIL = 'user@example.com'
    JIRA_API_TOKEN = 'jira_api_token'

    def test_action(self):
        with open(scriptdir('test_jira/test_request_ticket_data/test_input.json'), 'r') as f:
            input = json.load(f)

        action = RequestTicketData(issue='ABC-123')

        result = action.get_response(input)

        self.assertEqual(input, result)

    async def test_executor(self):
        with open(scriptdir('test_jira/test_request_ticket_data/test_input.json'), 'r') as f:
            input = json.load(f)

        adapter = TestHttpAdapter(request_result={
            TestHttpAdapter.Request(
                url='https://jira-host/rest/api/3/issue/ABC-123?expand=renderedFields,changelog',
                headers=(('Accept', 'application/json'),),
                auth=TestHttpAdapter.Auth(login=self.JIRA_EMAIL, password=self.JIRA_API_TOKEN),
            ) : (200, input)}
        )

        execute = async_executor.Executor(adapter)
        action = RequestTicketData(issue='ABC-123')

        result = await execute(action)
        self.assertEqual(input, result)

    async def test_raises_executor_exception_on_404(self):
        adapter = TestHttpAdapter(request_result={})

        execute = async_executor.Executor(adapter)
        action = RequestTicketData(issue='ABC-123')

        with self.assertRaises(ExecutorException) as exc_info:
            result = await execute(action)
        self.assertEqual(exc_info.exception.args[0], 404)


class CalculateTimelinesTestCase(unittest.TestCase):
    def test_one(self):
        input = get_module_from_file('test_jira/calculate_timelines/input.py')
        expected = get_module_from_file('test_jira/calculate_timelines/expected.py')
        issue_data = entities.IssueData(
            issue='ABC-123',
            history=json.loads(json_mapper.dumps(input.input)),
            issue_id = 123,
            project_id = 45,
            summary = 'Fix this',
            created=datetime(2024, 1, 18, 11, 5, 19, 636000,
                         tzinfo=tzoffset(None, 3600)),
            created_by='Someone Else',
        )
        timelines = tuple(calculate_timelines(issue_data, input.display_name))

        self.assertEqual(expected.expected, timelines)

    def test_with_from_long_long_ago(self):
        input = get_module_from_file('test_jira/calculate_timelines/input.py')
        expected = get_module_from_file('test_jira/calculate_timelines/expected.py')
        issue_data = entities.IssueData(
            issue='ABC-123',
            history=json.loads(json_mapper.dumps(input.input)),
            issue_id = 123,
            project_id = 45,
            summary = 'Fix this',
            created=datetime(2024, 1, 18, 11, 5, 19, 636000,
                         tzinfo=tzoffset(None, 3600)),
            created_by='Someone Else',
        )
        timelines = tuple(calculate_timelines(issue_data, input.display_name, from_=datetime(1990, 1, 1,0, 0, 0)))

        self.assertEqual(expected.expected, timelines)

