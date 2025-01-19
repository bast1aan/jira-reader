import json
import unittest

from bast1aan.jira_reader.jira import ComputeTicketHistory
from bast1aan.jira_reader import json_mapper
from tests.bast1aan.jira_reader.util import scriptdir, get_module_from_file


class AsdataclassTestCase(unittest.TestCase):
    maxDiff = None
    def test_with_compute_ticket_history(self):
        with open(scriptdir('test_jira/test_request_ticket_history/test_input.json'), 'r') as f:
            input = json.load(f)
        expected = get_module_from_file('test_jira/test_request_ticket_history/test_expected.py')

        action = ComputeTicketHistory()

        result = action.get_response(input)
        d = json_mapper.dumps(result)
        converted = json_mapper.asdataclass(ComputeTicketHistory.Response, json.loads(d))

        self.assertEqual(expected.expected, converted)

