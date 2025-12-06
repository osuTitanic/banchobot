
from app.common.database.repositories import beatmapsets, beatmaps
from app.common.database.objects import DBBeatmapset, DBBeatmap
from app.common.constants import BeatmapStatus
from app import beatmaps as beatmap_helper
from app.extensions.types import *
from app.cog import BaseCog

from discord import app_commands, Interaction, Attachment
from discord.ext.commands import Bot
from datetime import datetime

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
        fix_leadin_times: bool = False,
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
        
        # Update slider multiplier values inside database
        await self.run_async(
            beatmap_helper.update_slider_multiplier,
            database_set
        )

        await self.update_beatmapset(
            database_set.id,
            {'osz_filesize': filesize, 'osz_filesize_novideo': filesize_novideo}
        )

        if move_to_pending:
            await self.update_beatmapset(
                database_set.id,
                {'status': BeatmapStatus.Pending.value}
            )
            await self.update_beatmaps_by_set_id(
                database_set.id,
                {'status': BeatmapStatus.Pending.value}
            )

        followup = f"Successfully added [{database_set.full_name}](http://osu.{config.DOMAIN_NAME}/s/{database_set.id}) to Titanic!"

        if round_decimal_values:
            updates = await self.run_async(
                beatmap_helper.fix_beatmap_decimal_values,
                database_set
            )
            followup += f"\n(Fixed {len(updates)}/{len(database_set.beatmaps)} beatmaps with decimal values)"

        if fix_leadin_times:
            updates = await self.run_async(
                beatmap_helper.fix_beatmap_lead_in,
                database_set
            )
            followup += f"\n(Fixed lead-in times for {len(updates)}/{len(database_set.beatmaps)} beatmaps)"

        # TODO: Discord webhook updates
        return await interaction.followup.send(followup)

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

        if beatmapset.status >= BeatmapStatus.Ranked:
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

        if beatmap.status >= BeatmapStatus.Ranked:
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
        status = BeatmapStatus.from_lowercase(status_type)
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
        
        if status >= BeatmapStatus.Ranked:
            await self.update_beatmapset(
                beatmapset.id,
                {'approved_at': datetime.now()}
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
        status = BeatmapStatus.from_lowercase(status_type)
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

    @app_commands.command(name="downloadset", description="Move the files of a beatmapset from Bancho to Titanic")
    @app_commands.check(role_check)
    async def download_beatmapset_command(
        self,
        interaction: Interaction,
        beatmapset_id: int
    ) -> None:
        if not (beatmapset := await self.fetch_beatmapset(beatmapset_id)):
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset_id}` does not exist on Titanic!",
                ephemeral=True
            )
            
        if beatmapset.server != 0 or beatmapset.download_server != 0:
            return await interaction.response.send_message(
                f"Beatmapset `{beatmapset.full_name}` is already hosted on Titanic!",
                ephemeral=True
            )

        await interaction.response.defer()
        response_details = []

        background_file = await self.run_async(
            self.storage.get_background,
            f"{beatmapset_id}l"
        )
        audio_file = await self.run_async(
            self.storage.get_mp3,
            beatmapset_id
        )

        if background_file is not None:
            await self.run_async(
                self.storage.upload_background,
                beatmapset_id, background_file
            )

        if audio_file is not None:
            await self.run_async(
                self.storage.upload_mp3,
                beatmapset_id, audio_file
            )

        for beatmap in beatmapset.beatmaps:
            osu_file = await self.run_async(
                self.storage.get_beatmap,
                beatmap.id
            )

            if osu_file is None:
                response_details.append(f"- Beatmap `{beatmap.id}`: .osu file not found")
                continue

            await self.run_async(
                self.storage.upload_beatmap_file,
                beatmap.id, osu_file
            )

        osz_response = await self.run_async(
            self.storage.get_osz,
            beatmapset_id
        )

        if osz_response is not None:
            await self.run_async(
                self.storage.upload_osz,
                beatmapset_id, b"".join(osz_response)
            )
        else:
            response_details.append(
                f"- Beatmapset `{beatmapset.id}`: .osz file not found"
            )

        await self.update_beatmapset(
            beatmapset.id,
            {'download_server': 1}
        )
        return await interaction.followup.send(
            f"Successfully moved all files for [{beatmapset.full_name}](http://osu.{config.DOMAIN_NAME}/s/{beatmapset.id}) to Titanic!\n" +
            "\n".join(response_details)
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
