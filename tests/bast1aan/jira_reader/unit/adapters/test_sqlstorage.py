import unittest
from datetime import datetime, timedelta

import sqlalchemy.exc

from bast1aan.jira_reader import entities
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.sqlstorage import Base
from tests.bast1aan.jira_reader.adapters.sqlstorage import TestSQLStorage


class TestRequest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = TestSQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()
        await self.storage.clean_up()

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

    async def test_cannot_have_same_issue_at_same_time(self) -> None:
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

    async def test_issue_cannot_be_null(self) -> None:
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

class TestIssueData(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = TestSQLStorage(AlembicSQLInitializer(Base.metadata))
        await self.storage.set_up()
        await self.storage.clean_up()

    async def test(self) -> None:
        ent = entities.IssueData(
            issue='ABC-123',
            computed=datetime.now(),
            history=[
                {'some': 'object'},
            ],
            issue_id=123,
            project_id=45,
            summary='We need to fix this',
        )
        await self.storage.save_issue_data(ent)

        saved_ent = await self.storage.get_issue_data('ABC-123')

        self.assertEqual(ent, saved_ent)

    async def test_cannot_have_same_issue_at_same_time(self) -> None:
        now = datetime.now()
        req1 = entities.IssueData(
            issue='ABC-123',
            computed=now,
            history=[],
            issue_id=0,
            project_id=0,
            summary='',
        )
        req2 = entities.IssueData(
            issue='ABC-123',
            computed=now,
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='',
        )
        self.assertNotEqual(req1, req2)
        await self.storage.save_issue_data(req1)
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as e:
            await self.storage.save_issue_data(req2)
        self.assertIn('UNIQUE constraint failed', str(e.exception))

    async def test_issue_cannot_be_null(self) -> None:
        req_url_none = entities.IssueData(
            issue=None,  # type: ignore
            computed=datetime.now(),
            history=[],
            issue_id=0,
            project_id=0,
            summary='',
        )
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as e:
            await self.storage.save_issue_data(req_url_none)
        self.assertIn('NOT NULL constraint failed', str(e.exception))

    async def test_computed_is_default_now(self) -> None:
        now = datetime.now()
        req_url_none = entities.IssueData(
            issue='ABC-123',
            computed=None,  # type: ignore
            history=[],
            issue_id=0,
            project_id=0,
            summary='',
        )
        await self.storage.save_issue_data(req_url_none)

        saved_req = await self.storage.get_issue_data('ABC-123')

        self.assertGreaterEqual(saved_req.computed, now)

    async def test_result_may_be_none_because_it_is_serialized_to_string(self) -> None:
        req_url_none = entities.IssueData(
            issue='ABC-123',
            computed=datetime.now(),
            history=None,
            issue_id=0,
            project_id=0,
            summary='',
        )
        await self.storage.save_issue_data(req_url_none)

        saved_req = await self.storage.get_issue_data('ABC-123')

        self.assertIsNone(saved_req.history)

    async def test_get_recent_issue_datas(self) -> None:

        now = datetime.now()
        yesterday = now - timedelta(days=1)

        abc123_yesterday = entities.IssueData(
            issue='ABC-123',
            computed=yesterday,
            history=[],
            issue_id=0,
            project_id=0,
            summary='yesterday',
        )
        abc123_today = entities.IssueData(
            issue='ABC-123',
            computed=now,
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='today',
        )
        abc456_today = entities.IssueData(
            issue='ABC-456',
            computed=now,
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='today',
        )
        await self.storage.save_issue_data(abc123_yesterday)
        await self.storage.save_issue_data(abc123_today)
        await self.storage.save_issue_data(abc456_today)

        result = [issue_data async for issue_data in self.storage.get_recent_issue_datas()]

        self.assertCountEqual([abc123_today, abc456_today], result)

    async def test_save_issuedata_updates_existing_if_already_in_db(self) -> None:
        now = datetime.now()
        ent = entities.IssueData(
            issue='ABC-123',
            computed=now,
            history=[
                {'some': 'object'},
            ],
            issue_id=123,
            project_id=45,
            summary='We need to fix this',
        )
        await self.storage.save_issue_data(ent)

        saved_ent = await self.storage.get_issue_data('ABC-123')

        saved_ent.issue_id = 456

        await self.storage.save_issue_data(saved_ent)

        objs = [obj async for obj in self.storage.get_issue_datas()]

        self.assertEqual([
            entities.IssueData(
                issue='ABC-123',
                computed=now,
                history=[
                    {'some': 'object'},
                ],
                issue_id=456,
                project_id=45,
                summary='We need to fix this',
            )], objs)

    async def test_get_recent_issue_datas_with_computed_filter(self) -> None:

        now = datetime.now()
        yesterday = now - timedelta(days=1)

        abc99 = entities.IssueData(
            issue='ABC-99',
            computed=yesterday - timedelta(days=1),
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='long ago',
        )

        abc123_yesterday = entities.IssueData(
            issue='ABC-123',
            computed=yesterday,
            history=[],
            issue_id=0,
            project_id=0,
            summary='yesterday',
        )
        abc123_today = entities.IssueData(
            issue='ABC-123',
            computed=now,
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='today',
        )
        abc456_today = entities.IssueData(
            issue='ABC-456',
            computed=now,
            history=[{'some': 'other'}],
            issue_id=0,
            project_id=0,
            summary='today',
        )
        await self.storage.save_issue_data(abc99)
        await self.storage.save_issue_data(abc123_yesterday)
        await self.storage.save_issue_data(abc123_today)
        await self.storage.save_issue_data(abc456_today)

        result = [issue_data async for issue_data in self.storage.get_recent_issue_datas(from_=now - timedelta(hours=12))]

        self.assertCountEqual([abc123_today, abc456_today], result)
