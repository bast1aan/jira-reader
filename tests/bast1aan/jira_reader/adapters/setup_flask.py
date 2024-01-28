import hypercorn.config
import hypercorn.asyncio
import bast1aan.jira_reader.rest_api
import asyncio


def setup_flask(socket_path: str) -> asyncio.Task[None]:
    config = hypercorn.config.Config()
    config.bind = f'unix:{socket_path}'
    config.server_names = ['flask']
    config.debug = True
    return asyncio.create_task(
        hypercorn.asyncio.serve(
            bast1aan.jira_reader.rest_api.app,
            config,
            mode='wsgi'
        )
    )

