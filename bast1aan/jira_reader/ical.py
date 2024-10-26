""" implementation to create ical file from calendar objects """
from typing import Iterable

import icalendar

from . import calendar

def to_ical(calendar: calendar.Calendar, events: Iterable[calendar.Event]) -> bytes:
    ical_calendar = icalendar.Calendar()
    ical_calendar['X-WR-CALNAME'] = calendar.calendar_name
    for event in events:
        ical_event = icalendar.Event()
        ical_event['uid'] = event.id
        ical_event['dtstart'] = event.start.strftime('%Y%m%dT%H%M%S')
        ical_event['dtend'] = event.end.strftime('%Y%m%dT%H%M%S')
        ical_event.add('categories', event.categories)
        ical_event['summary'] = event.summary
        ical_event['url'] = event.url

        ical_calendar.add_component(ical_event)
    return ical_calendar.to_ical()

