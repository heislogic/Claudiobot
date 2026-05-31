import discord
from discord.ext import commands
from config import TOKEN
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Cog carregado: {filename}")
            except Exception as e:
                print(f"Erro ao carregar cog {filename}: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    await load_cogs()
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro sync: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)