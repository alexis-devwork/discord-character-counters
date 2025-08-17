import discord
from config import TOKEN
from utils import MyBot

intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True

bot = MyBot(command_prefix="/avct", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def setup_cogs():
    await bot.load_extension("avct_cog")


if __name__ == "__main__":
    import asyncio

    asyncio.run(setup_cogs())
    bot.run(TOKEN)
