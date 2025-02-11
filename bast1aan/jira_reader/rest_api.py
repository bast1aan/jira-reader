import json
from dataclasses import asdict
from datetime import datetime

from flask import Flask, Response, request as flask_request

from bast1aan.jira_reader import json_mapper, calendar
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.async_executor import AioHttpAdapter
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage, Base
from bast1aan.jira_reader.async_executor import Executor, ExecutorException
from bast1aan.jira_reader.entities import Request, IssueData, JSONable
from bast1aan.jira_reader.ical import to_ical
from bast1aan.jira_reader.jira import RequestTicketData, ComputeTicketHistory, calculate_timelines

app = Flask(__name__)

@app.post("/api/jira/fetch-data/<issue>")
async def fetch_data_post(issue: str) -> Response:
    storage = await _sql_storage()
    action = RequestTicketData(issue)
    execute = Executor(AioHttpAdapter())
    try:
        result = await execute(action)
        await storage.save_request(Request(issue=issue, result=result))
    except ExecutorException as e:
        return _result_response(e.args[1], status=e.args[0])
    return _result_response(result, status=201)

@app.get("/api/jira/fetch-data/<issue>")
async def fetch_data_get(issue: str) -> Response:
    storage = await _sql_storage()
    latest_request = await storage.get_latest_request(issue)
    if not latest_request:
        return _result_response({"error": "Issue not found in database"}, status=404)
    return _result_response(latest_request.result)

def _result_response(result: JSONable, status: int = 200) -> Response:
    return app.response_class(json.dumps(result), mimetype="application/json", status=status)

@app.post("/api/jira/compute-history/<issue>")
async def compute_history(issue: str) -> Response:
    storage = await _sql_storage()
    latest_issue_data = await storage.get_issue_data(issue)
    latest_request = await storage.get_latest_request(issue)
    created = False
    if _history_is_outdated(latest_request, latest_issue_data):
        if not latest_request:
            return app.response_class('{"error": "Issue not found in database"}', mimetype="application/json",
                                      status=404)
        result = latest_request.result
        action = ComputeTicketHistory()
        history = action.get_response(result)
        latest_issue_data = IssueData(
            issue=issue,
            history={
                "items": [asdict(item) for item in history.items],
                "comments": [asdict(comment) for comment in history.comments],
            },
            issue_id=history.issue_id,
            project_id=history.project_id,
            summary=history.summary,
            created=history.created,
            created_by=history.created_by,
        )
        latest_issue_data = await storage.save_issue_data(latest_issue_data)
        created = True
    return app.response_class(json_mapper.dumps(latest_issue_data), status=201 if created else 200, mimetype="application/json")

def _history_is_outdated(latest_request: Request | None, latest_issue_data: IssueData | None) -> bool:
    return not latest_issue_data or not latest_request or \
        latest_request.requested > latest_issue_data.computed or \
        latest_issue_data.created_by is None or latest_issue_data.created is None

@app.route("/api/jira/timeline/<display_name>")
async def timeline(display_name: str) -> Response:
    storage = await _sql_storage()

    from_ = None
    if 'from' in flask_request.args:
        from_ = datetime.fromisoformat(flask_request.args['from'])

    results = [
        timeline
            async for issue_data in storage.get_recent_issue_datas(from_=from_)
            for timeline in calculate_timelines(issue_data, display_name, from_=from_)
    ]
    return app.response_class(json_mapper.dumps({'results': results}), mimetype="application/json")

@app.route("/api/jira/timeline-ical/<display_name>")
async def timeline_as_ical(display_name: str) -> Response:
    storage = await _sql_storage()

    from_ = None
    if 'from' in flask_request.args:
        from_ = datetime.fromisoformat(flask_request.args['from'])

    events = [
        calendar.event_from_timeline(timeline)
            async for issue_data in storage.get_recent_issue_datas(from_=from_)
            for timeline in calculate_timelines(issue_data, display_name, from_=from_)
    ]

    ical_body = to_ical(
        calendar.Calendar(
            calendar_name='jira-reader %s' % display_name
        ),
        events
    )

    return app.response_class(
        response=ical_body,
        mimetype="text/calendar",
        headers={'Content-Disposition': 'attachment; filename="jira-reader {}.ics"'.format(display_name)}
    )

_storage = None

async def _sql_storage() -> SQLStorage:
    """ One storage instance per app """
    global _storage
    if not _storage:
        _storage = SQLStorage(AlembicSQLInitializer(Base.metadata))
        await _storage.set_up()
    return _storage
