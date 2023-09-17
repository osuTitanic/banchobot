
from typing import List, Callable
from dataclasses import dataclass
from discord import Member

@dataclass
class Command:
    function: Callable
    triggers: List[str]
    roles: List[str]

    def has_permission(self, member: Member) -> bool:
        """Check if member has permission to execute this command"""
        member_roles = [role.name for role in member.roles]

        for role in self.roles:
            if role in member_roles:
                return True

        return False
