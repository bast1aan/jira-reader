import unittest
from datetime import datetime

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters import sqlstorage


class TestSqlStorage(unittest.TestCase):
    def test(self):
        sqlstorage.set_up()

        req = entities.Request(
            url='http://some_url',
            requested=datetime.now(),
            result=[
                {'some': 'object'},
            ]
        )
        sqlstorage.save_request(req)

        saved_req = sqlstorage.get_latest_request('http://some_url')

        self.assertEqual(req, saved_req)
