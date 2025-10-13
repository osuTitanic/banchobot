
from app.common.database.repositories import scores
from app.common.database.objects import DBScore
from app.common.constants import Mods
from app.extensions.types import *
from discord.ext.commands import Bot
from discord.ext import commands
from discord import Embed, Color
from app.cog import BaseCog

import config
import app

class PPRecord(BaseCog):
    @commands.hybrid_command("pprecord", description="Displays the current pp record")
    async def pp_record(
        self,
        ctx: commands.Context,
        mods: str | None = None
    ) -> None:
        mods_value = Mods.from_string(mods).value if mods else None

        standard = await self.fetch_pp_record(0, mods_value)
        taiko = await self.fetch_pp_record(1, mods_value)
        catch = await self.fetch_pp_record(2, mods_value)
        mania = await self.fetch_pp_record(3, mods_value)

        embed = Embed(title="PP Records", color=Color.blue())
        embed.add_field(name="Standard", value=self.format_score(standard), inline=False)
        embed.add_field(name="Taiko", value=self.format_score(taiko), inline=False)
        embed.add_field(name="Catch", value=self.format_score(catch), inline=False)
        embed.add_field(name="Mania", value=self.format_score(mania), inline=False)
        await ctx.send(embed=embed, reference=ctx.message)

    async def fetch_pp_record(self, mode: int, mods: int | None = None) -> DBScore | None:
        with self.database.managed_session() as session:
            result = await self.run_async(
                scores.fetch_pp_record,
                mode, mods, True, session
            )

            if not result:
                return None

            # Preload beatmap & user relationships
            result.user
            result.beatmap
            result.beatmap.beatmapset
            return result

    @staticmethod
    def format_score(score: DBScore) -> str:
        if not score:
            return "No score for this mode :("

        score_str = f"{score.beatmap.full_name} +{Mods(score.mods).short}\n{score.pp:.2f}pp {score.acc*100:.2f}%"
        score_str += f" {score.grade} [{score.n300}/{score.n100}/{score.n50}/{score.nMiss}]"
        user_str = f"[{score.user.name}](http://osu.{config.DOMAIN_NAME}/u/{score.user_id})"
        return f"{score_str} by {user_str}"

async def setup(bot: Bot):
    await bot.add_cog(PPRecord())
