from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import icalendar


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

def to_ical(calendar: Calendar, events: Sequence[Event]) -> bytes:
    ical_calendar = icalendar.Calendar()
    ical_calendar['X-WR-CALNAME'] = calendar.calendar_name
    for event in events:
        ical_event = icalendar.Event()
        ical_event['uid'] = event.id
        ical_event['dtstart'] = event.start.strftime('%Y%m%dT%H%M%S')
        ical_event['dtend'] = event.end.strftime('%Y%m%dT%H%M%S')
        ical_event.add('categories', event.categories)
        ical_event['summary'] = event.summary

        ical_calendar.add_component(ical_event)
    return ical_calendar.to_ical()

