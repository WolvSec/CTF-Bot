import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, List

import discord
import jsonpickle
from decouple import config
from discord.ext import commands

from ctfbot import ctftime

JSON_DATA_FILE = 'data.json'

HEADERS = {
    'User-Agent': 'CTFTime Discord Bot/0.1.0'
}


def iso_to_pretty(iso):
    return datetime.datetime.fromisoformat(iso).strftime("%B %d at %I%p")


@dataclass
class ServerData:
    events: DefaultDict[int, int] = field(default_factory=lambda: defaultdict(int))
    archived_events: List[int] = field(default_factory=list)


@dataclass
class GlobalData:
    servers: DefaultDict[int, ServerData] = field(default_factory=lambda: defaultdict(ServerData))


class CtfBot(commands.Bot):

    async def on_connect(self):
        return await super().on_connect()

    async def on_command_error(self, ctx: discord.ApplicationContext, exception):
        await ctx.respond(f'Error while executing command: `{exception}`')


class CtfCog(commands.Cog):
    data: GlobalData = None

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
        with open(JSON_DATA_FILE, 'w') as file:
            file.write(jsonpickle.encode(self.data, indent=4))

    def load_data(self):
        try:
            with open('data.json') as file:
                self.data = jsonpickle.decode(file.read())
        except OSError:
            print("Couldn't read default config file")
            self.data = GlobalData()
            self.write_data()

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    async def upcoming(self, ctx: discord.ApplicationContext):
        events = ctftime.get_upcoming()
        await ctx.respond(f'Found {len(events)} events in the next week:')
        for event in events:
            await ctx.respond(embed=self.create_event_embed(event))

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    async def schedule(self, ctx: discord.ApplicationContext):
        events = self.data.servers[ctx.guild_id].events
        if events:
            description = '\n'.join(bot.get_channel(int(channel_id)).mention
                                    for channel_id in events.values())
            embed = discord.Embed(title='Upcoming registered events', description=description)
            await ctx.respond(embed=embed)
        else:
            await ctx.respond('No upcoming events at the moment')

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    async def event(self, ctx: discord.ApplicationContext, event_id: discord.Option(int)):
        event = ctftime.get_event(event_id)
        await ctx.respond(embed=self.create_event_embed(event))

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    @commands.has_permissions(administrator=True)
    async def register(self, ctx: discord.ApplicationContext,
                       event_id: discord.Option(int), channel_name: discord.Option(str)):
        data = self.data.servers[ctx.guild_id]
        if str(event_id) in data.events or str(event_id) in data.archived_events:
            await ctx.respond('You have already registered/played this event!')
        else:
            event = ctftime.get_event(event_id)
            guild: discord.Guild = ctx.guild
            category: discord.CategoryChannel = guild.get_channel(config('CTF_CATEGORY_ID', cast=int))
            channel: discord.TextChannel = await guild.create_text_channel(name=channel_name, category=category)
            message: discord.Message = await channel.send(embed=self.create_event_embed(event))
            await message.pin()
            data.events[event_id] = channel.id
            self.write_data()

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    @commands.has_permissions(administrator=True)
    async def archive(self, ctx: discord.ApplicationContext):
        guild: discord.Guild = ctx.guild
        category: discord.CategoryChannel = guild.get_channel(config('ARCHIVE_CATEGORY_ID', cast=int))
        data = self.data.servers[ctx.guild_id]
        for event_id, channel_id in data.events.items():
            if int(channel_id) == ctx.channel_id:
                await ctx.channel.edit(category=category)
                del data.events[event_id]
                data.archived_events.append(event_id)
                self.write_data()
                await ctx.respond('Done!')
                return
        await ctx.respond('Current channel is not an active CTF')

    @commands.slash_command(guild_ids=[config('GUILD_ID', cast=int)])
    async def team(self, ctx: discord.ApplicationContext, team_id: discord.Option(int)):
        team = ctftime.get_team(team_id)
        embed = discord.Embed(title=team['primary_alias'])
        columns = defaultdict(str)
        for year in team['rating']:
            rating = team['rating'][year]
            columns['Year'] += year + '\n'
            if 'rating_place' in rating:
                columns['Rank'] += str(rating['rating_place'])
            columns['Rank'] += '\n'
            if 'rating_points' in rating:
                columns['Points'] += f'{rating["rating_points"]:.1f}' + " "
            columns['Points'] += '\n'
        for name, value in columns.items():
            embed.add_field(name=name, value=value)
        embed.set_thumbnail(url=team['logo'])
        await ctx.respond(embed=embed)


if __name__ == '__main__':
    bot = CtfBot()
    bot.add_cog(CtfCog())
    bot.run(config('TOKEN'))
