import unittest
from datetime import datetime

import sqlalchemy.exc

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage


class TestSqlStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = SQLStorage()
        await self.storage.set_up()

    async def test(self) -> None:
        req = entities.Request(
            url='http://some_url',
            requested=datetime.now(),
            result=[
                {'some': 'object'},
            ]
        )
        await self.storage.save_request(req)

        saved_req = await self.storage.get_latest_request('http://some_url')

        self.assertEqual(req, saved_req)

    async def test_cannot_have_same_url_at_same_time(self) -> None:
        now = datetime.now()
        req1 = entities.Request(
            url='http://some_url',
            requested=now,
            result=[]
        )
        req2 = entities.Request(
            url='http://some_url',
            requested=now,
            result=[{'some': 'other'}]
        )
        self.assertNotEqual(req1, req2)
        await self.storage.save_request(req1)
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as e:
            await self.storage.save_request(req2)
        self.assertIn('UNIQUE constraint failed', str(e.exception))
