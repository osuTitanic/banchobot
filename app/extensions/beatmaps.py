
# TODO: /downloadset - Download a beatmapset from bancho to local storage

from app.common.database.repositories import beatmapsets, beatmaps
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.constants import DatabaseStatus
from app import beatmaps as beatmap_helper
from app.extensions.types import *
from app.cog import BaseCog

from discord import app_commands, Interaction, Attachment
from discord.ext.commands import Bot

import hashlib
import config

ALLOWED_ROLE_IDS = {config.STAFF_ROLE_ID, config.BAT_ROLE_ID}

def role_check(interaction: Interaction) -> bool:
    return any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles)

class BeatmapManagement(BaseCog):
    @app_commands.command(name="addset", description="Add a beatmapset from bancho to Titanic!")
    @app_commands.check(role_check)
    async def add_beatmapset(
        self,
        interaction: Interaction,
        beatmapset_id: int,
        round_decimal_values: bool = True,
        move_to_pending: bool = True
    ) -> None:
        if not self.ossapi:
            return await interaction.response.send_message(
                "I am not configured to use the osu!api.",
                ephemeral=True
            )

        if await self.fetch_beatmapset(beatmapset_id):
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset_id}` was already added to Titanic!",
                ephemeral=True
            )

        try:
            ossapi_set = await self.ossapi.beatmapset(beatmapset_id)
            assert ossapi_set is not None
        except (ValueError, AssertionError):
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset_id}` does not exist on bancho!",
                ephemeral=True
            )

        await interaction.response.defer()

        database_set = await self.run_async(
            beatmap_helper.store_ossapi_beatmapset,
            ossapi_set
        )

        filesize, filesize_novideo = await self.run_async(
            beatmap_helper.fetch_osz_filesizes,
            database_set.id
        )

        await self.update_beatmapset(
            database_set.id,
            {'osz_filesize': filesize, 'osz_filesize_novideo': filesize_novideo}
        )

        if move_to_pending:
            await self.update_beatmapset(
                database_set.id,
                {'status': DatabaseStatus.Pending.value}
            )
            await self.update_beatmaps_by_set_id(
                database_set.id,
                {'status': DatabaseStatus.Pending.value}
            )

        if not round_decimal_values:
            return await interaction.followup.send(
                f"Successfully added [{database_set.full_name}](http://osu.{config.DOMAIN_NAME}/s/{database_set.id}) to Titanic!"
            )

        updates = await self.run_async(
            beatmap_helper.fix_beatmap_files,
            database_set
        )

        # TODO: Discord webhook updates
        return await interaction.followup.send(
            f"Successfully added [{database_set.full_name}](http://osu.{config.DOMAIN_NAME}/s/{database_set.id}) to Titanic!\n"
            f"(Fixed {len(updates)}/{len(database_set.beatmaps)} beatmaps with decimal values)"
        )

    @app_commands.command(name="deleteset", description="Delete a beatmapset from Titanic's database")
    @app_commands.check(role_check)
    async def delete_beatmapset_command(
        self,
        interaction: Interaction,
        beatmapset_id: int
    ) -> None:
        beatmapset = await self.fetch_beatmapset(beatmapset_id)

        if not beatmapset:
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset_id}` does not exist on Titanic!",
                ephemeral=True
            )

        if beatmapset.status >= DatabaseStatus.Ranked:
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset.full_name}` was approved and cannot be deleted!",
                ephemeral=True
            )

        await interaction.response.defer()
        await self.run_async(
            beatmap_helper.delete_beatmapset,
            beatmapset
        )

        return await interaction.followup.send(
            f"Successfully deleted beatmapset `{beatmapset.full_name}`!"
        )

    @app_commands.command(name="deletemap", description="Delete a single beatmap from Titanic's database")
    @app_commands.check(role_check)
    async def delete_beatmap_command(
        self,
        interaction: Interaction,
        beatmap_id: int
    ) -> None:
        beatmap = await self.fetch_beatmap(beatmap_id)

        if not beatmap:
            return await interaction.response.send_message(
                f"Beatmap `{beatmap_id}` does not exist on Titanic!",
                ephemeral=True
            )

        if beatmap.status >= DatabaseStatus.Ranked:
            return await interaction.response.send_message(
                f"Beatmap `{beatmap.full_name}` was approved and cannot be deleted!",
                ephemeral=True
            )
            
        if len(beatmap.beatmapset.beatmaps) <= 1:
            return await interaction.response.send_message(
                f"Beatmap `{beatmap.full_name}` is the only map in its set, please use `/deleteset {beatmap.set_id}` instead!",
                ephemeral=True
            )

        await interaction.response.defer()
        await self.run_async(
            beatmap_helper.delete_beatmap,
            beatmap
        )

        return await interaction.followup.send(
            f"Successfully deleted beatmap `{beatmap.full_name}`!"
        )
        
    @app_commands.command(name="modset", description="Modify a beatmapset's status")
    @app_commands.check(role_check)
    async def modify_beatmapset_command(
        self,
        interaction: Interaction,
        beatmapset_id: int,
        status_type: StatusType
    ) -> None:
        status = DatabaseStatus.from_lowercase(status_type)
        beatmapset = await self.fetch_beatmapset(beatmapset_id)

        if not beatmapset:
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset_id}` does not exist on Titanic!",
                ephemeral=True
            )

        await interaction.response.defer()
        await self.update_beatmapset(
            beatmapset.id,
            {'status': status.value}
        )
        await self.update_beatmaps_by_set_id(
            beatmapset.id,
            {'status': status.value}
        )

        # TODO: Discord webhook updates
        return await interaction.followup.send(
            f"Successfully updated the status of [{beatmapset.full_name}](http://osu.{config.DOMAIN_NAME}/s/{beatmapset.id}) to `{status.name}`!"
        )
        
    @app_commands.command(name="moddiff", description="Modify a single beatmap's status")
    @app_commands.check(role_check)
    async def modify_beatmap_command(
        self,
        interaction: Interaction,
        beatmap_id: int,
        status_type: StatusType
    ) -> None:
        status = DatabaseStatus.from_lowercase(status_type)
        beatmap = await self.fetch_beatmap(beatmap_id)

        if not beatmap:
            return await interaction.response.send_message(
                f"Beatmap `{beatmap_id}` does not exist on Titanic!",
                ephemeral=True
            )

        await interaction.response.defer()
        await self.update_beatmap(
            beatmap.id,
            {'status': status.value}
        )

        # TODO: Discord webhook updates
        return await interaction.followup.send(
            f"Successfully updated the status of [{beatmap.full_name}](http://osu.{config.DOMAIN_NAME}/b/{beatmap.id}) to `{status.name}`!"
        )

    @app_commands.command(name="uploadmap", description="Upload and replace single beatmap's .osu file")
    @app_commands.check(role_check)
    async def upload_beatmap_command(
        self,
        interaction: Interaction,
        file: Attachment,
        beatmap_id: int
    ) -> None:
        beatmap = await self.fetch_beatmap(beatmap_id)

        if not beatmap:
            return await interaction.response.send_message(
                f"Beatmap `{beatmap_id}` does not exist on Titanic!",
                ephemeral=True
            )

        await interaction.response.defer()
        file = await file.read()

        await self.run_async(
            self.storage.upload_beatmap_file,
            beatmap.id, file
        )
        await self.update_beatmap(
            beatmap.id,
            {'md5': hashlib.md5(file).hexdigest()}
        )

        return await interaction.followup.send(
            f"Successfully replaced the .osu file for [{beatmap.full_name}](http://osu.{config.DOMAIN_NAME}/b/{beatmap.id})!"
        )

    async def fetch_beatmapset(self, beatmapset_id: int) -> DBBeatmapset | None:
        with self.database.managed_session() as session:
            beatmapset = await self.run_async(
                beatmapsets.fetch_one,
                beatmapset_id, session
            )

            if not beatmapset:
                return None

            # Preload beatmaps relationship
            beatmapset.beatmaps
            return beatmapset

    async def fetch_beatmap(self, beatmap_id: int) -> DBBeatmap | None:
        with self.database.managed_session() as session:
            beatmap = await self.run_async(
                beatmaps.fetch_by_id,
                beatmap_id, session
            )

            if not beatmap:
                return None

            # Preload beatmapset relationship
            beatmap.beatmapset
            beatmap.beatmapset.beatmaps
            return beatmap

    async def update_beatmapset(self, set_id: int, updates: dict) -> int:
        return await self.run_async(
            beatmapsets.update,
            set_id, updates
        )

    async def update_beatmaps_by_set_id(self, set_id: int, updates: dict) -> int:
        return await self.run_async(
            beatmaps.update_by_set_id,
            set_id, updates
        )

    async def update_beatmap(self, beatmap_id: int, updates: dict) -> int:
        return await self.run_async(
            beatmaps.update,
            beatmap_id, updates
        )

async def setup(bot: Bot):
    await bot.add_cog(BeatmapManagement())
