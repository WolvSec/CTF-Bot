from decouple import config

from ctfbot.bot import CtfBot
from ctfbot.cog import CtfCog

if __name__ == '__main__':
    bot = CtfBot()
    bot.add_cog(CtfCog())
    bot.run(config('TOKEN'))
