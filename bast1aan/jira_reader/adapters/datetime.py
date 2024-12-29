import datetime
import os


def now() -> datetime.datetime:
    return datetime.datetime.fromisoformat(os.environ['DATETIME_NOW']) if 'DATETIME_NOW' in os.environ else datetime.datetime.now()
