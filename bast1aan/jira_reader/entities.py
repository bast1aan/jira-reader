from dataclasses import dataclass
from datetime import datetime

JSON = list | dict | str

@dataclass
class Request:
    url: str
    requested: datetime
    result: JSON

