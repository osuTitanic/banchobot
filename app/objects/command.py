
from typing import List, Callable, Union
from dataclasses import dataclass
from discord import Member, User

@dataclass
class Command:
    function: Callable
    triggers: List[str]
    roles: List[str]

    def has_permission(self, member: Union[Member, User]) -> bool:
        """Check if member has permission to execute this command"""
        if not self.roles:
            # Command does not require permissions
            return True

        if type(member) != Member:
            return False

        member_roles = [role.name for role in member.roles]

        for role in self.roles:
            if role in member_roles:
                return True

        return False
