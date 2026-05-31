import discord
from discord.ext import commands
from discord import app_commands
from config import CARGO_STAFF_ID, CANAL_STAFF_ID
from database import db
from views.formulario_views import ViewStaff

class FormularioAlistamento(discord.ui.Modal, title="🥷 Wanted Formulário 🥷"):
    nickname = discord.ui.TextInput(label="Nickname", placeholder="Seu nickname in-game", required=True, max_length=32)
    classe = discord.ui.TextInput(label="Classe", placeholder="Ex: DPS, TANK, HEALER", required=True, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        cargos_membro = [role.name.upper() for role in interaction.user.roles]
        classes_validas = ["DPS", "HEALER", "TANK"]
        cargo_existente = any(classe in cargos_membro for classe in classes_validas)

        if cargo_existente:
            await interaction.response.send_message(
                "❌ Você já é membro da guilda e não pode enviar um novo formulário.",
                ephemeral=True
            )
            return

        canal_staff = interaction.client.get_channel(CANAL_STAFF_ID)
        if canal_staff:
            embed = discord.Embed(title="📋 Formulário enviado", color=discord.Color.orange())
            embed.add_field(name="Usuario", value=interaction.user.mention, inline=False)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="Classe", value=self.classe.value, inline=True)
            embed.set_footer(text=f"ID: {interaction.user.id}")
            view = ViewStaff(interaction.user, self.nickname.value, self.classe.value)
            msg = await canal_staff.send(
                content=f"<@&{CARGO_STAFF_ID}> novo formulário enviado por {interaction.user.mention}!",
                embed=embed,
                view=view
            )
            db.adicionar_formulario_pendente(
                message_id=msg.id,
                channel_id=CANAL_STAFF_ID,
                user_id=interaction.user.id,
                nickname=self.nickname.value,
                classe=self.classe.value
            )
        await interaction.response.send_message("✅ Formulário enviado! Aguarde a análise da staff.", ephemeral=True)

class FormularioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="formulario", description="Envia o formulário de recrutamento")
    @app_commands.default_permissions(administrator=True)
    async def slash_formulario(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🥷 Wanted Formulário 🥷",
            description="Deseja entrar na Wanted? Clique no botão abaixo para preencher o formulário.",
            color=discord.Color.blue()
        )
        view = ViewFormulario()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Formulário enviado!", ephemeral=True)

class ViewFormulario(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Preencher Formulário", style=discord.ButtonStyle.green, custom_id="btn_formulario")
    async def btn_formulario(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FormularioAlistamento())

async def setup(bot):
    await bot.add_cog(FormularioCog(bot))