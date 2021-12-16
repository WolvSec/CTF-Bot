import discord
from discord.ext import commands


class CtfBot(commands.Bot):

    async def on_connect(self):
        return await super().on_connect()

    async def on_command_error(self, ctx: discord.ApplicationContext, exception):
        await ctx.respond(f'Error while executing command: `{exception}`')
