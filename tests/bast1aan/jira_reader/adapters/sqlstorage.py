from sqlalchemy import text

from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage


class TestSQLStorage(SQLStorage):
    async def clean_up(self):
        async with self._async_session() as session:
            await session.execute(text('DELETE FROM requests'))
