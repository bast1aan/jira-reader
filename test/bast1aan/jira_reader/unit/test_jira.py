import dataclasses
import os
import importlib.util
import json
import types
import typing
import unittest

from bast1aan.jira_reader.jira import RequestTicketHistory, RequestTicketHistoryResponse


def fix_field_types(cls):
    hints = typing.get_type_hints(cls, globalns=None, localns=None)
    for field in dataclasses.fields(cls):
        field.type = hints[field.name]


class TestRequestTicketHistory(unittest.TestCase):
    def test(self):
        with open('test_jira/test_request_ticket_history/test_input.json', 'r') as f:
            input = json.load(f)
        expected = get_module_from_file('test_jira/test_request_ticket_history/test_expected.py')

        fix_field_types(RequestTicketHistoryResponse.Item.Action)
        fix_field_types(RequestTicketHistoryResponse.Item)
        fix_field_types(RequestTicketHistoryResponse)

        print(dataclasses.fields(RequestTicketHistoryResponse.Item))
        action = RequestTicketHistory(issue='ABC-123')

        result = action.get_response(input)

        self.assertEqual(expected.expected, result)

def get_module_from_file(path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
