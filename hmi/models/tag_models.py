from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TagDefinition:
    name: str
    group: str
    area: str
    address: int
    data_type: str
    access: str
    scale: float = 1.0
    default: Any = None
    alarm: bool = False
    alarm_when: Any = None
    alarm_text: str = ""


@dataclass
class TagValue:
    definition: TagDefinition
    value: Any = None
    quality: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AlarmRecord:
    timestamp: str
    tag_name: str
    text: str
    value: Any
    state: str