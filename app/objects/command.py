
from typing import List, Callable
from dataclasses import dataclass

@dataclass
class Command:
    function: Callable
    triggers: List[str]
    roles: List[str]
