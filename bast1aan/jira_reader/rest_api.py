from dataclasses import asdict

from flask import Flask, Response

from bast1aan.jira_reader import json_mapper
from bast1aan.jira_reader.adapters.async_executor import AioHttpAdapter
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage
from bast1aan.jira_reader.async_executor import Executor
from bast1aan.jira_reader.entities import Request
from bast1aan.jira_reader.jira import RequestTicketHistory

app = Flask(__name__)

@app.route("/api/jira/request-ticket-history/<issue>")
async def index(issue: str) -> Response:
    storage = _sql_storage()
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

def _sql_storage() -> SQLStorage:
    """ One storage instance per app """
    global _storage
    if not _storage:
        _storage = SQLStorage()
    return _storage
