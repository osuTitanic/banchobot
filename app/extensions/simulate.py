
from discord import app_commands, Interaction, Embed
from discord.ext.commands import Bot

from app.common.config import config_instance as config
from app.common.database.objects import DBBeatmap, DBScore
from app.common.database.repositories import beatmaps
from app.common.helpers import performance
from app.common.constants import Mods
from app.extensions.types import *
from app.cog import BaseCog

class SimulateScore(BaseCog):
    @app_commands.command(name="simulate", description="Simulate pp for a beatmap")
    async def simulate_score(
        self,
        interaction: Interaction,
        beatmap_id: int,
        mods: str = "NM",
        mode: ModeType | None = None,
        combo: int | None = None,
        accuracy: float = 100.0,
        misses: int = 0
    ) -> None:
        if not (beatmap := await self.resolve_beatmap(beatmap_id)):
            return await interaction.response.send_message(
                "I could not find that beatmap.",
                ephemeral=True
            )

        await interaction.response.defer()

        target_mods = Mods.from_string(mods).value
        target_mode = Modes.get(mode, beatmap.mode)

        difficulty = await self.calculate_difficulty(
            beatmap,
            target_mode,
            target_mods
        )

        simulated_score = DBScore()
        simulated_score.beatmap_id = beatmap.id
        simulated_score.beatmap = beatmap
        simulated_score.mods = target_mods
        simulated_score.mode = target_mode
        simulated_score.acc = accuracy / 100.0
        simulated_score.nMiss = misses
        simulated_score.max_combo = combo or beatmap.max_combo
        simulated_score.n300 = beatmap.count_normal + beatmap.count_slider + beatmap.count_spinner
        simulated_score.n100 = 0
        simulated_score.n50 = 0
        simulated_score.nGeki = 0
        simulated_score.nKatu = 0
        result = await self.calculate_ppv2(simulated_score)

        embed = self.create_embed(result, difficulty, beatmap, mods)
        await interaction.followup.send(embed=embed)

    async def resolve_beatmap(self, beatmap_id: int) -> DBBeatmap | None:
        return await self.run_async(
            beatmaps.fetch_by_id,
            beatmap_id
        )
        
    async def calculate_difficulty(
        self,
        beatmap: DBBeatmap,
        mode: int,
        mods: Mods
    ) -> performance.ppv2.DifficultyAttributes:
        return await self.run_async(
            performance.calculate_difficulty_from_id,
            beatmap.id,
            mode,
            mods
        )
        
    async def calculate_ppv2(
        self,
        score: DBScore
    ) -> float | None:
        return await self.run_async(
            performance.calculate_ppv2,
            score
        )

    def create_embed(
        self,
        pp: float,
        result: performance.ppv2.DifficultyAttributes,
        beatmap: DBBeatmap,
        mods: str
    ) -> Embed:
        embed = Embed(
            title=beatmap.full_name,
            url=f"http://osu.{config.DOMAIN_NAME}/b/{beatmap.id}",
            description=(
                f"**PP:** {pp:.2f}\n"
                f"**Stars:** {result.star_rating:.2f}★\n" +
                (f"**Mods:** +{mods}" if mods != "NM" else "")
            )
        )
        embed.set_footer(text="Simulated Score")
        embed.set_thumbnail(url=self.thumbnail_url(beatmap.beatmapset))

        for attribute, value in result.difficulty_attributes.items():
            embed.add_field(
                name=attribute.replace("_", " ").title(),
                value=f"{value:.2f}",
                inline=True
            )

        return embed

async def setup(bot: Bot):
    await bot.add_cog(SimulateScore())
