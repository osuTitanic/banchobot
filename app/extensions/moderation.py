
# TODO: /wipescores - Wipe scores from a beatmap or beatmapset

from app.common.database.objects import DBGroupEntry, DBUser, DBName, DBGroup
from app.common.database.repositories import groups, names
from app.common.constants import regexes
from app.extensions.types import *
from app.cog import BaseCog

from discord import app_commands, Interaction
from discord.ext.commands import Bot
from typing import List

class Moderation(BaseCog):
    @app_commands.command(name="restrict", description="Restrict a user")
    @app_commands.default_permissions(ban_members=True)
    async def restrict_user(
        self,
        interaction: Interaction,
        identifier: str,
        reason: str = "No reason."
    ) -> None:
        if not (user := await self.resolve_user_from_identifier(identifier)):
            return await interaction.response.send_message(
                f"I could not find that user: `{identifier}`.",
                ephemeral=True
            )

        if user.restricted:
            return await interaction.response.send_message(
                f"User `{user.name}` is already restricted.",
                ephemeral=True
            )

        # Let bancho handle the restriction
        await self.submit_event(
            'restrict',
            user.id, reason
        )

        await interaction.response.send_message(
            f"User `{user.name}` has been restricted."
        )

    @app_commands.command(name="unrestrict", description="Unrestrict a user")
    @app_commands.default_permissions(ban_members=True)
    async def unrestrict_user(
        self,
        interaction: Interaction,
        identifier: str,
        restore_scores: bool = True
    ) -> None:
        if not (user := await self.resolve_user_from_identifier(identifier)):
            return await interaction.response.send_message(
                f"I could not find that user: `{identifier}`.",
                ephemeral=True
            )

        if not user.restricted:
            return await interaction.response.send_message(
                f"User `{user.name}` is not restricted.",
                ephemeral=True
            )

        # Let bancho handle the unrestriction
        await self.submit_event(
            'unrestrict',
            user.id, restore_scores
        )

        await interaction.response.send_message(
            f"User `{user.name}` has been unrestricted."
        )

    @app_commands.command(name="rename", description="Rename a user")
    @app_commands.default_permissions(moderate_members=True)
    async def rename_user(
        self,
        interaction: Interaction,
        identifier: str,
        new_name: str
    ) -> None:
        new_name = new_name.strip()
        safe_name = new_name.lower().replace(" ", "_")

        if len(new_name) < 3:
            return await interaction.response.send_message(
                "Usernames must be at least 3 characters long.",
                ephemeral=True
            )

        if len(new_name) > 15:
            return await interaction.response.send_message(
                "Usernames cannot be longer than 15 characters.",
                ephemeral=True
            )

        if new_name.lower().endswith("_old"):
            return await interaction.response.send_message(
                "Usernames cannot end with `_old`.",
                ephemeral=True
            )

        if new_name.lower().startswith("deleteduser"):
            return await interaction.response.send_message(
                "This username is not allowed.",
                ephemeral=True
            )

        name_match = regexes.USERNAME.match(new_name)

        if not name_match:
            return await interaction.response.send_message(
                "This username contains invalid characters.",
                ephemeral=True
            )

        if not (user := await self.resolve_user_from_identifier(identifier)):
            return await interaction.response.send_message(
                f"I could not find that user: `{identifier}`.",
                ephemeral=True
            )

        if await self.resolve_user_by_safe_name(safe_name):
            return await interaction.response.send_message(
                "This username is already taken.",
                ephemeral=True
            )

        if reserved_name := await self.fetch_reserved_name(new_name):
            if reserved_name.user_id != user.id:
                return await interaction.response.send_message(
                    "This username is reserved.",
                    ephemeral=True
                )

        past_names = await self.fetch_name_history(user.id)
        max_name_changes = 4

        if len(past_names) >= max_name_changes:
            # User has exceeded the maximum amount of name changes
            # We want to now find the oldest entry & un-reserve it, so
            # that other people can use it again.
            oldest_entry = sorted(past_names, key=lambda name: name.id)[0]

            await self.update_name_history_entry(
                oldest_entry.id,
                {"reserved": False}
            )

        await self.create_name_history_entry(user.id, user.name)
        await self.update_user(user.id, {"name": new_name, "safe_name": safe_name})

        await interaction.response.send_message(
            (f"User `{user.name}` has been renamed to `{new_name}`.") +
            (" Their old name has been un-reserved." if len(past_names) >= max_name_changes else "")
        )

    @app_commands.command(name="addgroup", description="Add a user to a group")
    @app_commands.default_permissions(administrator=True)
    async def add_to_group(
        self,
        interaction: Interaction,
        identifier: str,
        group: str
    ) -> None:
        if not (user := await self.resolve_user_from_identifier(identifier)):
            return await interaction.response.send_message(
                f"I could not find that user: `{identifier}`.",
                ephemeral=True
            )

        group_list = await self.fetch_groups()
        group_map = {g.name.lower(): g for g in group_list}
        group_map.update({g.short_name.lower(): g for g in group_list})

        if group.lower() not in group_map:
            return await interaction.response.send_message(
                f"I could not find that group: `{group}`.",
                ephemeral=True
            )

        group_object = group_map[group.lower()]
        
        try:
            await self.create_group_entry(user.id, group_object.id)
        except Exception as e:
            return await interaction.response.send_message(
                f"User `{user.name}` is already in group `{group_object.name}`.",
                ephemeral=True
            )
            
        await interaction.response.send_message(
            f"User `{user.name}` has been added to group `{group_object.name}`."
        )

    @app_commands.command(name="removegroup", description="Remove a user from a group")
    @app_commands.default_permissions(administrator=True)
    async def remove_from_group(
        self,
        interaction: Interaction,
        identifier: str,
        group: str
    ) -> None:
        if not (user := await self.resolve_user_from_identifier(identifier)):
            return await interaction.response.send_message(
                f"I could not find that user: `{identifier}`.",
                ephemeral=True
            )

        group_list = await self.fetch_groups()
        group_map = {g.name.lower(): g for g in group_list}
        group_map.update({g.short_name.lower(): g for g in group_list})
        
        if group.lower() not in group_map:
            return await interaction.response.send_message(
                f"I could not find that group: `{group}`.",
                ephemeral=True
            )
            
        group_object = group_map[group.lower()]
        success = await self.delete_group_entry(user.id, group_object.id)
        
        if not success:
            return await interaction.response.send_message(
                f"User `{user.name}` is not in group `{group_object.name}`.",
                ephemeral=True
            )
            
        await interaction.response.send_message(
            f"User `{user.name}` has been removed from group `{group_object.name}`."
        )

    async def fetch_groups(self) -> List[DBGroup]:
        return await self.run_async(
            groups.fetch_all
        )

    async def create_group_entry(self, user_id: int, group_id: int) -> DBGroupEntry:
        return await self.run_async(
            groups.create_entry,
            user_id, group_id
        )
        
    async def delete_group_entry(self, user_id: int, group_id: int) -> int:
        return await self.run_async(
            groups.delete_entry,
            user_id, group_id
        )

    async def create_name_history_entry(self, user_id: int, old_name: str) -> DBName:
        return await self.run_async(
            names.create,
            user_id, old_name
        )

    async def fetch_reserved_name(self, name: str) -> DBName | None:
        return await self.run_async(
            names.fetch_by_name_reserved,
            name
        )

    async def fetch_name_history(self, user_id: int) -> List[DBName]:
        return await self.run_async(
            names.fetch_all,
            user_id
        )

    async def update_name_history_entry(self, id: int, data: dict) -> int:
        return await self.run_async(
            names.update,
            id, data
        )

    async def resolve_user_from_identifier(self, identifier: str) -> DBUser | None:
        if identifier.isnumeric():
            return await self.resolve_user_by_id(int(identifier))

        if identifier.startswith("<@") and identifier.endswith(">"):
            discord_id = identifier[2:-1]
            discord_id = discord_id.strip("!")

            if discord_id.isnumeric():
                return await self.resolve_user(int(discord_id))

        return await self.resolve_user_by_name_case_insensitive(identifier)

async def setup(bot: Bot):
    await bot.add_cog(Moderation())
