from collections import defaultdict
from datetime import datetime
from pathlib import Path

import discord
import jsonpickle

from decouple import config
from discord.ext import commands

from ctfbot import ctftime
from ctfbot.data import GlobalData

JSON_DATA_FILE = Path.cwd() / 'data.json'


def iso_to_pretty(iso):
    return datetime.fromisoformat(iso).strftime("%B %d at %I%p")


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

    def __init__(self, bot):
        self.load_data()
        self.bot = bot
        # self.scheduler = sched.scheduler(datetime.utcnow, time.sleep)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await ctx.respond("An internal error occurred")

    def write_data(self):
        JSON_DATA_FILE.write_text(jsonpickle.encode(self.data, indent=4))

    def load_data(self):
        try:
            self.data = jsonpickle.decode(JSON_DATA_FILE.read_text())
            # for server in self.data.servers.values():
            #     for reminder in server.reminders.values():
            #         self.scheduler.enter(reminder.utcnow(), 1, lambda: self.)
        except OSError:
            print("Couldn't read default data file")
            self.data = GlobalData()
            self.write_data()

    @commands.slash_command()
    async def upcoming(self, ctx: discord.ApplicationContext):
        events = ctftime.get_upcoming()
        await ctx.respond(f'Found {len(events)} events in the next week:')
        for event in events:
            await ctx.respond(embed=self.create_event_embed(event))

    @commands.slash_command()
    async def schedule(self, ctx: discord.ApplicationContext):
        events = self.data.servers[ctx.guild_id].events
        if events:
            description = '\n'.join(ctx.bot.get_channel(int(channel_id)).mention
                                    for channel_id in events.values())
            embed = discord.Embed(title='Upcoming registered events', description=description)
            await ctx.respond(embed=embed)
        else:
            await ctx.respond('No upcoming events at the moment')

    @commands.slash_command()
    async def event(self, ctx: discord.ApplicationContext, event_id: discord.Option(int)):
        event = ctftime.get_event(event_id)
        if event is None:
            await ctx.respond("Event not found")
            return
        await ctx.respond(embed=self.create_event_embed(event))

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def register(self, ctx: discord.ApplicationContext,
                       event_id: discord.Option(int), category_name: discord.Option(str)):
        data = self.data.servers[ctx.guild_id]
        if str(event_id) in data.events or str(event_id) in data.archived_events:
            await ctx.respond('You have already registered/played this event!')
            return
        event = ctftime.get_event(event_id)
        if event is None:
            await ctx.respond('Event not found')
            return
        guild: discord.Guild = ctx.guild
        category: discord.CategoryChannel = await guild.create_category(name=category_name,
                                                                        position=config('CTF_CATEGORY_POS'))
        data.events[event_id] = category.id
        overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=False,
                                                                      add_reactions=False, manage_threads=False)}
        channel_join: discord.TextChannel = await guild.create_text_channel(name='join-ctf',
                                                                            category=category, overwrites=overwrites)
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
        channel_join_logs: discord.TextChannel = await guild.create_text_channel(name='logs',
                                                                                 category=category,
                                                                                 overwrites=overwrites)
        channel_challenges: discord.TextChannel = await guild.create_text_channel(name='challenges',
                                                                                  category=category,
                                                                                  overwrites=overwrites)
        channel_general: discord.TextChannel = await guild.create_text_channel(name='general',
                                                                               category=category,
                                                                               overwrites=overwrites)
        message_challenges_embed = discord.Embed(
            title=f"{category_name} Challenges",
            description="Current and solved challenges. To add a challenge, use the command /challenge in" +
            f"{channel_general.mention}. To solve a challenge, use the command /solve in a challenge thread." +
            "If you created a challenge by mistake, contact an admin to use /remove",
            color=discord.Colour.yellow(),
        )
        message_challenges: discord.Message = await channel_challenges.send(embed=message_challenges_embed)
        message_info: discord.Message = await channel_join.send(embed=self.create_event_embed(event))
        message_join_embed = discord.Embed(
            title=f"Join {category_name}",
            description="To join the CTF, react with the :white_check_mark: emoji below!" +
            " You must have the CTF-Verified role to join. Please message an admin/officer to obtain this role.",
            color=discord.Colour.green(),
        )
        message_join: discord.Message = await channel_join.send(embed=message_join_embed)
        await message_join.add_reaction("✅")
        await ctx.respond(f"Event Created! Join at {channel_join.mention}")
        self.write_data()

    @commands.slash_command()
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

    @commands.slash_command()
    async def team(self, ctx: discord.ApplicationContext, team_id: discord.Option(int)):
        team = ctftime.get_team(team_id)
        if team is None:
            await ctx.respond("Team not found")
            return
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

    @commands.slash_command()
    async def reminder(self, ctx: discord.ApplicationContext):
        data = self.data.servers[ctx.guild_id]
        if ctx.channel_id in data.reminders:
            await ctx.respond('Removed reminder for this event')
            data.reminders[ctx.channel_id] = datetime.utcnow()
        else:
            await ctx.respond('Added reminder for this event')
            del data.reminders[ctx.channel_id]

    @commands.slash_command()
    async def challenge(self, ctx: discord.ApplicationContext, chal_category: discord.Option(str),
                        chal_name: discord.Option(str)):
        banned_strings = ['→', '**', '~~', '@']
        if any(banned_string in chal_category or banned_string in chal_name for banned_string in banned_strings):
            await ctx.respond('Invalid character in challenge name/category')
            return
        guild: discord.Guild = ctx.guild
        data = self.data.servers[ctx.guild_id]
        for event_id, category_id in data.events.items():
            category = guild.get_channel(category_id)
            if category and ctx.channel_id == category.channels[3].id:
                break
        else:
            await ctx.respond('This is not a CTF channel')
            return
        channel_challenges: discord.TextChannel = category.channels[2]
        channel_general: discord.TextChannel = category.channels[3]
        message_challs: discord.Message = await channel_challenges.fetch_message(channel_challenges.last_message_id)
        embed = message_challs.embeds[0]
        thread = None
        for index, field in enumerate(embed.fields):
            if field.name == f'**{chal_category}**':
                for i in range(index + 1, len(embed.fields)):
                    if embed.fields[i].value.startswith(chal_name):
                        await ctx.respond('Challenge already exists')
                        return
                    elif embed.fields[i].name.startswith('**'):
                        break
                else:
                    i = len(embed.fields)
                break
        else:
            embed.add_field(name=f'**{chal_category}**', value='')
            i = len(embed.fields)

        thread = await channel_general.create_thread(name=chal_category + '/' + chal_name, type=discord.ChannelType.public_thread)
        embed.insert_field_at(i, name='', value=chal_name + ' → ' + thread.mention, inline=False)

        await message_challs.edit(embed=embed)
        await ctx.respond(f'Challenge created {thread.mention}')

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx: discord.ApplicationContext, chal_category: discord.Option(str),
                     chal_name: discord.Option(str)):
        guild: discord.Guild = ctx.guild
        data = self.data.servers[ctx.guild_id]
        for event_id, category_id in data.events.items():
            category = guild.get_channel(category_id)
            if category and ctx.channel_id == category.channels[3].id:
                break
        else:
            await ctx.respond('This is not a CTF channel')
            return
        channel_challenges: discord.TextChannel = category.channels[2]
        message_challs: discord.Message = await channel_challenges.fetch_message(channel_challenges.last_message_id)
        embed = message_challenges.embeds[0]
        for index, field in enumerate(embed.fields):
            if field.name == f'**{chal_category}**':
                for i in range(index + 1, len(embed.fields)):
                    if embed.fields[i].value.startswith(chal_name):
                        thread_id = int(embed.fields[i].value.split(' → <#')[1].split('>')[0])
                        thread: discord.Thread = guild.get_thread(thread_id)
                        await thread.edit(archived=True)
                        embed.remove_field(i)
                        if embed.fields[i - 1].name.startswith('**') and (i == len(embed.fields) or
                           embed.fields[i].name.startswith('**')):
                            embed.remove_field(i - 1)
                        await message_challs.edit(embed=embed)
                        await ctx.respond('Challenge removed')
                        return
        await ctx.respond('Challenge not found')

    @commands.slash_command()
    async def solve(self, ctx: discord.ApplicationContext, flag: discord.Option(str),
                    display_flag: discord.Option(bool)):
        guild: discord.Guild = ctx.guild
        data = self.data.servers[ctx.guild_id]
        found_thread = False
        for event_id, category_id in data.events.items():
            category = guild.get_channel(category_id)
            channel_challs: discord.TextChannel = category.channels[2]
            message_challs: discord.Message = await channel_challs.fetch_message(channel_challs.last_message_id)
            embed = message_challs.embeds[0]
            for index, field in enumerate(embed.fields):
                if not field.name.startswith('**'):
                    thread_id = int(field.value.split(' → <#')[1].split('>')[0])
                    if (ctx.channel_id == thread_id):
                        embed_field = embed.fields[index]
                        found_thread = True
                        break
            if found_thread:
                break
        else:
            await ctx.respond('This is not a CTF thread')
            return
        if (embed_field.value.startswith('~~')):
            await ctx.respond('Challenge already solved')
            return
        challenge_name = embed_field.value.split(' → ')[0]
        if not display_flag:
            flag = "HIDDEN"
        message_challenges_embed = discord.Embed(
            title=f"{challenge_name} has been solved!",
            description=f"{ctx.author.mention} has solved with flag: {flag}",
            color=discord.Colour.green(),
        )
        message_solve: discord.Message = await category.channels[3].send(embed=message_challenges_embed)
        embed.set_field_at(index, name='', value="~~" + embed_field.value + '~~ has been solved by ' +
                           ctx.author.mention + '!', inline=False)
        await message_challs.edit(embed=embed)
        await ctx.respond('Flag submitted!')

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def print_events(self, ctx: discord.ApplicationContext):
        data = self.data.servers[ctx.guild_id]
        if data.events == {}:
            await ctx.respond('No events')
            return
        for event_id, category_id in data.events.items():
            await ctx.respond(f'{event_id}: {category_id}')

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def set_event_category_id(self, ctx: discord.ApplicationContext, event_id: discord.Option(int),
                                    category_id: discord.Option(str)):
        data = self.data.servers[ctx.guild_id]
        if event_id in data.events:
            await ctx.respond('Event id already exists')
            return
        data.events[event_id] = int(category_id)
        await ctx.respond(f'Added event {event_id} with category {category_id}')

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def remove_event(self, ctx: discord.ApplicationContext, event_id: discord.Option(int)):
        data = self.data.servers[ctx.guild_id]
        if event_id not in data.events:
            await ctx.respond('Event id does not exist')
            return
        data.events.pop(event_id)
        await ctx.respond(f'Removed event {event_id}')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return
        guild = self.bot.get_guild(payload.guild_id)
        data = self.data.servers[guild.id]
        for event_id, category_id in data.events.items():
            category = guild.get_channel(category_id)
            if category and payload.channel_id == category.channels[0].id:
                break
        else:
            return
        player = await guild.fetch_member(payload.user_id)
        if discord.utils.get(guild.roles, id=config('CTF_VERIFIED_ROLE_ID', cast=int)) not in player.roles:
            player = await bot.fetch_user(payload.user_id)
            await player.send('You do not have the CTF-Verified role! Please contact an admin to get this role.')
            return
        await category.channels[1].set_permissions(player, read_messages=True, send_messages=False,
                                                   add_reactions=False, manage_threads=False)
        await category.channels[2].set_permissions(player, read_messages=True, send_messages=False,
                                                   add_reactions=False, manage_threads=False)
        await category.channels[3].set_permissions(player, read_messages=True)
        await category.channels[1].send(f'{player.mention} has joined the CTF!')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        data = self.data.servers[guild.id]
        for event_id, category_id in data.events.items():
            category = guild.get_channel(category_id)
            if category and payload.channel_id == category.channels[0].id:
                break
        else:
            return
        player = await guild.fetch_member(payload.user_id)
        await category.channels[1].set_permissions(player, read_messages=False)
        await category.channels[2].set_permissions(player, read_messages=False)
        await category.channels[3].set_permissions(player, read_messages=False)
        await category.channels[1].send(f'{player.mention} has left the CTF!')
