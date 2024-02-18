import unittest
from datetime import datetime

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage


class TestSqlStorage(unittest.IsolatedAsyncioTestCase):
    async def test(self):
        storage = SQLStorage()

        await storage.set_up()

        req = entities.Request(
            url='http://some_url',
            requested=datetime.now(),
            result=[
                {'some': 'object'},
            ]
        )
        await storage.save_request(req)

        saved_req = await storage.get_latest_request('http://some_url')

        self.assertEqual(req, saved_req)
