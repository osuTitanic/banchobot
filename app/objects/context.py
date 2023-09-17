
from dataclasses import dataclass
from discord import Message
from typing import List

@dataclass
class Context:
    command: str
    args: List[str]
    message: Message
