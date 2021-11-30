from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import DefaultDict, List


@dataclass
class ServerData:
    events: DefaultDict[int, int] = field(default_factory=lambda: defaultdict(int))
    archived_events: List[int] = field(default_factory=list)
    challenges: DefaultDict[int, List[int]] = field(default_factory=lambda: defaultdict(list))
    reminders: DefaultDict[int, datetime] = field(default_factory=lambda: defaultdict(datetime))


@dataclass
class GlobalData:
    servers: DefaultDict[int, ServerData] = field(default_factory=lambda: defaultdict(ServerData))
