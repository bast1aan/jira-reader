import json
from dataclasses import asdict

from flask import Flask, Response

from bast1aan.jira_reader import json_mapper, calendar
from bast1aan.jira_reader.adapters.alembic.jira_reader import AlembicSQLInitializer
from bast1aan.jira_reader.adapters.async_executor import AioHttpAdapter
from bast1aan.jira_reader.adapters.sqlstorage import SQLStorage, Base
from bast1aan.jira_reader.async_executor import Executor, ExecutorException
from bast1aan.jira_reader.entities import Request, IssueData
from bast1aan.jira_reader.ical import to_ical
from bast1aan.jira_reader.jira import RequestTicketData, ComputeTicketHistory, calculate_timelines

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
        try:
            result = await execute(action)
            await storage.save_request(Request(issue=issue, result=result))
        except ExecutorException as e:
            return app.response_class(json.dumps(e.args[1]), mimetype="application/json", status=e.args[0])
    return app.response_class(json.dumps(result), mimetype="application/json")

@app.route("/api/jira/compute-history/<issue>")
async def compute_history(issue: str) -> Response:
    storage = await _sql_storage()
    issue_data = await storage.get_issue_data(issue)
    if not issue_data:
        latest_request = await storage.get_latest_request(issue)
        if not latest_request:
            return app.response_class('{"error": "Issue not found in database"}', mimetype="application/json",
                                      status=404)
        result = latest_request.result
        action = ComputeTicketHistory()
        history = action.get_response(result)
        issue_data = IssueData(
            issue=issue,
            history={
                "items": [asdict(item) for item in history.items],
                "comments": [asdict(comment) for comment in history.comments],
            },
            issue_id=history.issue_id,
            project_id=history.project_id,
            summary=history.summary,
        )
        await storage.save_issue_data(issue_data)
    return app.response_class(json_mapper.dumps(issue_data), mimetype="application/json")

@app.route("/api/jira/timeline/<display_name>")
async def timeline(display_name: str) -> Response:
    storage = await _sql_storage()
    results = [
        timeline
            async for issue_data in storage.get_issue_datas()
            for timeline in calculate_timelines(issue_data, display_name)
    ]
    return app.response_class(json_mapper.dumps({'results': results}), mimetype="application/json")

@app.route("/api/jira/timeline-ical/<display_name>")
async def timeline_as_ical(display_name: str) -> Response:
    storage = await _sql_storage()

    events = [
        calendar.event_from_timeline(timeline)
            async for issue_data in storage.get_issue_datas()
            for timeline in calculate_timelines(issue_data, display_name)
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
