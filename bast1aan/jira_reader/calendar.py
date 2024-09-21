""" Calendar domain logic """
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Sequence

from bast1aan.jira_reader import json_mapper
from bast1aan.jira_reader.entities import Timeline


@dataclass
class Calendar:
    calendar_name: str

@dataclass
class Event:
    id: str
    start: datetime
    end: datetime
    categories: Sequence[str]
    summary: str

def event_from_timeline(timeline: Timeline) -> Event:
    return Event(
        id=_hash(timeline),
        start=timeline.start,
        end=timeline.end,
        categories=_get_categories(timeline),
        summary='%s %s' % (timeline.issue, timeline.type)
    )

def _hash(timeline: Timeline) -> str:
    return hashlib.md5(
        json_mapper.dumps(
            asdict(timeline)
        ).encode('utf-8')
    ).hexdigest()


def _get_categories(timeline: Timeline) -> Sequence[str]:
    categories = []
    if timeline.type in (Timeline.TYPE_ASSIGNED, Timeline.TYPE_ASSIGNED_2ND_DEVELOPER):
        categories.append('assigned')
    if timeline.type == Timeline.TYPE_ASSIGNED_2ND_DEVELOPER:
        categories.append('seconddeveloper')
    if timeline.type == Timeline.TYPE_IN_PROGESS:
        categories.append('inprogress')
    return categories
