
from typing import List, Callable, Optional
from app.objects import Command

class CommandManager:
    def __init__(self) -> None:
        self.commands: List[Command] = []

    def register(self, triggers: List[str], roles: List[str] = []):
        """Register a command

        `triggers`: List of strings that trigger the command

        `roles` (optional): List of role names that the user requires to execute the command
        """
        def wrapper(f: Callable):
            self.commands.append(
                Command(
                    function=f,
                    triggers=[trigger.lower() for trigger in triggers],
                    roles=roles
                )
            )
            return f

        return wrapper

    def get(self, trigger: str) -> Optional[Command]:
        """Get a command by any trigger"""
        for command in self.commands:
            if trigger.lower() in command.triggers:
                return command
        return None
