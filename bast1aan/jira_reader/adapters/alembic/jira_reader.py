from dataclasses import dataclass
from os.path import dirname

import sqlalchemy
import sqlalchemy.ext.asyncio

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory

from bast1aan.jira_reader.adapters import sqlstorage


def run_migrations(connection: sqlalchemy.Connection, metadata: sqlalchemy.MetaData) -> None:
    """ version of alembic.command, but using same connection. this is needed
        for in-memory connections.
    """
    config = Config()
    config.set_main_option("script_location", dirname(__file__))
    script = ScriptDirectory.from_config(config)
    with EnvironmentContext(
        config=config,
        script=script,
        fn=lambda rev, context: script._upgrade_revs('head', rev)
    ) as context:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()

@dataclass
class AlembicSQLInitializer(sqlstorage.SQLInitializer):
    """ SQL Storage Initializer implemented running Alembic migrations. """
    metadata: sqlalchemy.MetaData

    async def __call__(self, conn: sqlalchemy.ext.asyncio.AsyncConnection) -> None:
        await conn.run_sync(run_migrations, self.metadata)
