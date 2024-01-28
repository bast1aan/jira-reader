from flask import Flask, Response, jsonify

from bast1aan.jira_reader.adapters.async_executor import AioHttpAdapter
from bast1aan.jira_reader.async_executor import Executor
from bast1aan.jira_reader.jira import RequestTicketHistory

app = Flask(__name__)

@app.route("/api/jira/request-ticket-history/<issue>")
async def index(issue: str) -> Response:
    action = RequestTicketHistory(issue)
    execute = Executor(AioHttpAdapter())
    return jsonify(await execute(action))
