import unittest
from datetime import datetime

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage


class TestSqlStorage(unittest.TestCase):
    def test(self):
        storage = SQLStorage()

        storage.set_up()

        req = entities.Request(
            url='http://some_url',
            requested=datetime.now(),
            result=[
                {'some': 'object'},
            ]
        )
        storage.save_request(req)

        saved_req = storage.get_latest_request('http://some_url')

        self.assertEqual(req, saved_req)
