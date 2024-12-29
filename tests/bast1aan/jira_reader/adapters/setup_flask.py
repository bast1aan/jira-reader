import os
from datetime import datetime
import hypercorn.config
import hypercorn.asyncio
import bast1aan.jira_reader.rest_api
import asyncio


def setup_flask(socket_path: str, now: datetime | None = None) -> asyncio.Task[None]:
    config = hypercorn.config.Config.from_mapping(
        bind=f'unix:{socket_path}',
        server_names=['flask'],
    )

    async def serve() -> None:
        if now:
            os.environ['DATETIME_NOW'] = now.isoformat()

        try:
            await hypercorn.asyncio.serve(
                bast1aan.jira_reader.rest_api.app,
                config,
                mode='wsgi'
            )
        finally:
            os.environ.pop('DATETIME_NOW', None)

    return asyncio.create_task(serve())
