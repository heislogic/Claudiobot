import discord
from discord.ext import commands
from config import CARGO_STAFF_ID, CANAL_STAFF_ID
from database import db

class ModalRecusa(discord.ui.Modal, title="❌ Formulário Recusado ❌"):
    motivo = discord.ui.TextInput(label="Motivo", placeholder="Explique o motivo da recusa", required=True, max_length=500)
    def __init__(self, usuario: discord.Member, message_id: int, channel_id: int):
        super().__init__()
        self.usuario = usuario
        self.message_id = message_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.usuario.send(f"❌ Seu alistamento para **Wanted** foi recusado.\n**Motivo:** {self.motivo.value}")
        except discord.Forbidden:
            pass
        db.remover_formulario_pendente(self.message_id, self.channel_id)
        await interaction.response.send_message(f"Recusado! {self.usuario.mention} foi notificado.", ephemeral=True)

class ViewStaff(discord.ui.View):
    def __init__(self, usuario: discord.Member, nickname: str, classe: str):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.nickname = nickname
        self.classe = classe

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.green, custom_id="btn_aceitar")
    async def btn_aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        db.remover_formulario_pendente(interaction.message.id, interaction.channel_id)

        cargo = discord.utils.get(interaction.guild.roles, name=self.classe.upper())
        if cargo is None:
            await interaction.followup.send(f"⚠️ Cargo `{self.classe.upper()}` não encontrado!", ephemeral=True)
            return
        try:
            await self.usuario.add_roles(cargo)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Sem permissão para adicionar o cargo `{cargo.name}`.", ephemeral=True)
            return
        try:
            await self.usuario.edit(nick=self.nickname)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Cargo adicionado, mas sem permissão para alterar o nickname.", ephemeral=True)

        # Aqui futuramente chamaremos a criação de ticket (será movido para ticket.py)
        # Por enquanto, manteremos a lógica de criação de canal aqui mesmo para simplificar, mas a ideia é que isso seja refatorado para o arquivo ticket.py
        # Para simplificar, vamos importar a função de criação do ticket do arquivo ticket.py
        from cogs.ticket import criar_ticket
        await criar_ticket(interaction, self.usuario, self.nickname, self.classe)

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="btn_recusar")
    async def btn_recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRecusa(self.usuario, interaction.message.id, interaction.channel_id))
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)