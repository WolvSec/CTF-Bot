import json
import datetime

import discord
import requests as requests
from decouple import config
from discord.ext import commands
from requests import HTTPError

import ctftime

HEADERS = {
    'User-Agent': 'WolvSec Discord Bot/0.1.0',
}


def iso_to_pretty(iso):
    return datetime.datetime.fromisoformat(iso).strftime("%B %d at %I%p")


class Ctf(commands.Cog):

    @commands.command()
    async def upcoming(self, ctx: commands.Context):
        events = ctftime.get_upcoming()
        await ctx.send(f'Found {len(events)} events in the next week:')
        for event in events:
            await ctx.send(embed=self.create_event_embed(event))

    @staticmethod
    def create_event_embed(event):
        embed = discord.Embed(title=event['title'], description=event['description'], url=event['ctftime_url'])
        embed.set_thumbnail(url=event['logo'])
        embed.add_field(name='Start', value=iso_to_pretty(event['start']))
        embed.add_field(name='Finish', value=iso_to_pretty(event['finish']))
        if event['weight'] > 1e-6:
            embed.add_field(name='Weight', value=event['weight'])
        return embed

    @commands.command()
    async def event(self, ctx: commands.Context, event_id: int):
        event = ctftime.get_event(event_id)
        await ctx.send(embed=self.create_event_embed(event))


if __name__ == '__main__':
    bot = commands.Bot(command_prefix=".")
    bot.add_cog(Ctf())
    bot.run(config('TOKEN'))


    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
