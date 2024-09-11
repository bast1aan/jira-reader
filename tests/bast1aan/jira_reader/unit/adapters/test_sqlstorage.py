import unittest
from datetime import datetime

import sqlalchemy.exc

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage, Base


class TestSqlStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = SQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()

    async def test(self) -> None:
        req = entities.Request(
            issue='ABC-123',
            requested=datetime.now(),
            result=[
                {'some': 'object'},
            ]
        )
        await self.storage.save_request(req)

        saved_req = await self.storage.get_latest_request('ABC-123')

        self.assertEqual(req, saved_req)

    async def test_cannot_have_same_url_at_same_time(self) -> None:
        now = datetime.now()
        req1 = entities.Request(
            issue='ABC-123',
            requested=now,
            result=[]
        )
        req2 = entities.Request(
            issue='ABC-123',
            requested=now,
            result=[{'some': 'other'}]
        )
        self.assertNotEqual(req1, req2)
        await self.storage.save_request(req1)
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as e:
            await self.storage.save_request(req2)
        self.assertIn('UNIQUE constraint failed', str(e.exception))

    async def test_url_cannot_be_null(self) -> None:
        req_url_none = entities.Request(
            issue=None,  # type: ignore
            requested=datetime.now(),
            result=[]
        )
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as e:
            await self.storage.save_request(req_url_none)
        self.assertIn('NOT NULL constraint failed', str(e.exception))

    async def test_requested_is_default_now(self) -> None:
        now = datetime.now()
        req_url_none = entities.Request(
            issue='ABC-123',
            requested=None,  # type: ignore
            result=[]
        )
        await self.storage.save_request(req_url_none)

        saved_req = await self.storage.get_latest_request('ABC-123')

        self.assertGreaterEqual(saved_req.requested, now)

    async def test_result_may_be_none_because_it_is_serialized_to_string(self) -> None:
        req_url_none = entities.Request(
            issue='ABC-123',
            requested=datetime.now(),
            result=None
        )
        await self.storage.save_request(req_url_none)

        saved_req = await self.storage.get_latest_request('ABC-123')

        self.assertIsNone(saved_req.result)
