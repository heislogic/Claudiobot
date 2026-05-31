import discord
from discord.ext import commands
from config import TOKEN
from database import db
import os
from views.formulario_views import ViewStaff
from views.ticket_views import ViewDeletarTicket

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

    # Restaurar formulários pendentes
    pendentes = db.listar_formularios_pendentes()
    for key, dados in pendentes.items():
        channel = bot.get_channel(dados["channel_id"])
        if channel:
            try:
                mensagem = await channel.fetch_message(dados["message_id"])
                guild = channel.guild
                usuario = guild.get_member(dados["user_id"])
                if usuario:
                    view = ViewStaff(usuario, dados["nickname"], dados["classe"])
                    bot.add_view(view, message_id=mensagem.id)
                    await mensagem.edit(view=view)
                else:
                    db.remover_formulario_pendente(dados["message_id"], dados["channel_id"])
            except discord.NotFound:
                db.remover_formulario_pendente(dados["message_id"], dados["channel_id"])
            except Exception as e:
                print(f"Erro ao restaurar formulário {key}: {e}")

    # Restaurar tickets ativos
    tickets = db.listar_tickets_ativos()
    for key, dados in tickets.items():
        channel = bot.get_channel(dados["channel_id"])
        if channel:
            try:
                mensagem = await channel.fetch_message(dados["message_id"])
                guild = channel.guild
                dono = guild.get_member(dados["dono_id"])
                if dono:
                    view = ViewDeletarTicket(channel, dono)
                    bot.add_view(view, message_id=mensagem.id)
                    await mensagem.edit(view=view)
                else:
                    db.remover_ticket_ativo(dados["channel_id"], dados["dono_id"])
            except discord.NotFound:
                db.remover_ticket_ativo(dados["channel_id"], dados["dono_id"])
            except Exception as e:
                print(f"Erro ao restaurar ticket {key}: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)