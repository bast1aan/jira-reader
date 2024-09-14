import json
from dataclasses import asdict

from flask import Flask, Response

from bast1aan.jira_reader import json_mapper
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.async_executor import AioHttpAdapter
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage, Base
from bast1aan.jira_reader.async_executor import Executor
from bast1aan.jira_reader.entities import Request
from bast1aan.jira_reader.jira import RequestTicketHistory, RequestTicketData

app = Flask(__name__)

@app.route("/api/jira/fetch-data/<issue>")
async def fetch_data(issue: str) -> Response:
    storage = await _sql_storage()
    latest_request = await storage.get_latest_request(issue)
    if latest_request:
        result = latest_request.result
    else:
        action = RequestTicketData(issue)
        execute = Executor(AioHttpAdapter())
        result = await execute(action)
        await storage.save_request(Request(issue=issue, result=result))
    return app.response_class(json.dumps(result), mimetype="application/json")

@app.route("/api/jira/compute-history/<issue>")
async def compute_history(issue: str) -> Response:
    storage = await _sql_storage()
    latest_request = await storage.get_latest_request(issue)
    if latest_request:
        result = latest_request.result
    else:
        action = RequestTicketHistory(issue)
        execute = Executor(AioHttpAdapter())
        result = await execute(action)
        await storage.save_request(Request(issue=issue, result=asdict(result)))
    return app.response_class(json_mapper.dumps(result), mimetype="application/json")

_storage = None

async def _sql_storage() -> SQLStorage:
    """ One storage instance per app """
    global _storage
    if not _storage:
        _storage = SQLStorage(AlembicSQLInitializer(Base.metadata))
        await _storage.set_up()
    return _storage
