import json
import datetime

import requests as requests
from decouple import config
from discord.ext import commands

HEADERS = {
    'User-Agent': 'WolvSec Discord Bot',
}


class Ctf(commands.Cog):
    @commands.command()
    async def upcoming(self, ctx: commands.Context):
        start = datetime.datetime.utcnow()
        finish = start + datetime.timedelta(weeks=1)
        start_timestamp = int(start.timestamp())
        finish_timestamp = int(finish.timestamp())
        response = requests.get(
            f'https://ctftime.org/api/v1/events/?limit=100&start={start_timestamp}&finish={finish_timestamp}',
            headers=HEADERS)
        if response.ok:
            events = json.loads(response.content)
            print(events)
            message = f'Found {len(events)} events in the next week:\n'
            for event in events:
                event_start = datetime.datetime.fromisoformat(event['start'])
                event_finish = datetime.datetime.fromisoformat(event['finish'])
                message += f'{event_start.strftime("%B %d at %I%p")} to {event_finish.strftime("%B %d at %I%p")}: '
                message += event['url'] + '\n'
            await ctx.send(message)
        else:
            await ctx.send(f'Failed to get info: {response.status_code}')


if __name__ == '__main__':
    bot = commands.Bot(command_prefix=".")
    bot.add_cog(Ctf())
    bot.run(config('TOKEN'))


    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user}')
