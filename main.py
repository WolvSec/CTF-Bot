import dataclasses
import datetime
import json
from dataclasses import dataclass
from typing import Dict, List

import discord
from decouple import config
from discord.ext import commands
from discord.ext.commands import has_permissions

import ctftime

HEADERS = {
    'User-Agent': 'WolvSec Discord Bot/0.1.0'
}


def iso_to_pretty(iso):
    return datetime.datetime.fromisoformat(iso).strftime("%B %d at %I%p")


@dataclass
class Data:
    events: Dict[str, str]
    archived_events: List[str]


class CtfBot(commands.Bot):
    async def on_command_error(self, ctx: commands.Context, exception):
        await ctx.send(f'Error while executing command: `{exception}`')


class CtfCog(commands.Cog):
    data = None

    @staticmethod
    def create_event_embed(event):
        embed = discord.Embed(title=f'{event["title"]} — {event["id"]}',
                              description=event['description'],
                              url=event['ctftime_url'])
        embed.set_thumbnail(url=event['logo'])
        embed.add_field(name='Start', value=iso_to_pretty(event['start']))
        embed.add_field(name='Finish', value=iso_to_pretty(event['finish']))
        if event['weight'] > 1e-9:
            embed.add_field(name='Weight', value=event['weight'])
        return embed

    def __init__(self):
        self.load_data()

    def write_data(self):
        with open('data.json', 'w') as file:
            json.dump(dataclasses.asdict(self.data), file, indent=4)

    def load_data(self):
        try:
            with open('data.json') as file:
                self.data = Data(**json.load(file))
        except OSError:
            print("Couldn't read default config file")
            self.data = Data(events={}, archived_events=[])
            self.write_data()

    @commands.command()
    async def upcoming(self, ctx: commands.Context):
        events = ctftime.get_upcoming()
        await ctx.send(f'Found {len(events)} events in the next week:')
        for event in events:
            await ctx.send(embed=self.create_event_embed(event))

    @commands.command()
    async def schedule(self, ctx: commands.Context):
        if self.data.events:
            description = '\n'.join(bot.get_channel(int(channel_id)).mention
                                    for channel_id in self.data.events.values())
            embed = discord.Embed(title='Upcoming registered events', description=description)
            await ctx.send(embed=embed)
        else:
            await ctx.send('No upcoming events at the moment')

    @commands.command()
    async def event(self, ctx: commands.Context, event_id: int):
        event = ctftime.get_event(event_id)
        await ctx.send(embed=self.create_event_embed(event))

    @commands.command()
    @has_permissions(administrator=True)
    async def register(self, ctx: commands.Context, event_id: int, channel_name: str):
        if str(event_id) in self.data.events or str(event_id) in self.data.archived_events:
            await ctx.send('You have already registered/played this event!')
        else:
            event = ctftime.get_event(event_id)
            guild: discord.Guild = ctx.guild
            category: discord.CategoryChannel = guild.get_channel(config('CTF_CATEGORY_ID', cast=int))
            channel: discord.TextChannel = await guild.create_text_channel(name=channel_name, category=category)
            message: discord.Message = await channel.send(embed=self.create_event_embed(event))
            await message.pin()
            self.data.events[str(event_id)] = str(channel.id)
            self.write_data()

    @commands.command()
    @has_permissions(administrator=True)
    async def archive(self, ctx: commands.Context):
        guild: discord.Guild = ctx.guild
        category: discord.CategoryChannel = guild.get_channel(config('ARCHIVE_CATEGORY_ID', cast=int))
        for event_id, channel_id in self.data.events.items():
            if int(channel_id) == ctx.channel.id:
                await ctx.channel.edit(category=category)
                del self.data.events[event_id]
                self.data.archived_events.append(event_id)
                self.write_data()
                break


if __name__ == '__main__':
    bot = CtfBot(command_prefix=".")
    bot.add_cog(CtfCog())
    bot.run(config('TOKEN'))
