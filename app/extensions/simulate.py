
from rosu_pp_py import Performance, Beatmap, PerformanceAttributes
from discord import app_commands, Interaction, Embed
from discord.ext.commands import Bot

from app.common.config import config_instance as config
from app.common.database.repositories import beatmaps
from app.common.database.objects import DBBeatmap
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

        if not (beatmap_file := self.storage.get_beatmap(beatmap_id)):
            return await interaction.response.send_message(
                "I could not find that beatmap.",
                ephemeral=True
            )

        await interaction.response.defer()

        target_mods = Mods.from_string(mods).value
        target_mode = Modes.get(mode, beatmap.mode)

        converted_mode = performance.convert_mode(target_mode)
        beatmap_object = Beatmap(bytes=beatmap_file)
        beatmap_object.convert(converted_mode, target_mods)

        calculator = Performance(lazer=False)
        calculator.set_accuracy(accuracy)
        calculator.set_misses(misses)
        calculator.set_mods(target_mods)

        if combo is not None:
            calculator.set_combo(combo)

        result = calculator.calculate(beatmap_object)
        embed = self.create_embed(result, beatmap, mods)
        await interaction.followup.send(embed=embed)

    async def resolve_beatmap(self, beatmap_id: int) -> DBBeatmap | None:
        return await self.run_async(
            beatmaps.fetch_by_id,
            beatmap_id
        )
        
    def create_embed(
        self,
        result: PerformanceAttributes,
        beatmap: DBBeatmap,
        mods: str
    ) -> Embed:
        embed = Embed(
            title=beatmap.full_name,
            url=f"http://osu.{config.DOMAIN_NAME}/b/{beatmap.id}",
            description=(
                f"**PP:** {result.pp:.2f}\n"
                f"**Stars:** {result.difficulty.stars:.2f}★\n" +
                (f"**Mods:** +{mods}" if mods != "NM" else "")
            )
        )
        embed.set_footer(text="Simulated Score")
        embed.set_thumbnail(url=self.thumbnail_url(beatmap.beatmapset))
        return embed

async def setup(bot: Bot):
    await bot.add_cog(SimulateScore())
