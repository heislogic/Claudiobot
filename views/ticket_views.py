import discord
from config import CANAL_STAFF_ID, CARGO_STAFF_ID
from database import db

class ModalConfirmarDelete(discord.ui.Modal, title="🗑️ Confirmar exclusão do canal"):
    confirmacao = discord.ui.TextInput(
        label="Digite CONFIRMAR para deletar este canal",
        placeholder="CONFIRMAR",
        required=True,
        max_length=10
    )
    def __init__(self, canal: discord.TextChannel, dono: discord.Member):
        super().__init__()
        self.canal = canal
        self.dono = dono

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmacao.value != "CONFIRMAR":
            await interaction.response.send_message("❌ Exclusão cancelada: você não digitou CONFIRMAR corretamente.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        nome_canal = self.canal.name
        try:
            await self.canal.delete()
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Sem permissão para deletar este canal.", ephemeral=True)
            return
        except discord.NotFound:
            await interaction.followup.send("⚠️ Canal já foi deletado.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"⚠️ Erro ao deletar: {str(e)}", ephemeral=True)
            return

        db.remover_ticket_ativo(self.canal.id, self.dono.id)

        try:
            await self.dono.send(f"🗑️ Seu canal `{nome_canal}` foi deletado por {interaction.user.mention}.")
        except discord.Forbidden:
            pass

        canal_staff = interaction.guild.get_channel(CANAL_STAFF_ID)
        if canal_staff:
            try:
                await canal_staff.send(f"🗑️ Canal `{nome_canal}` deletado por {interaction.user.mention} (dono: {self.dono.mention})")
            except:
                pass

        await interaction.followup.send("✅ Canal deletado com sucesso!", ephemeral=True)

class ViewDeletarTicket(discord.ui.View):
    def __init__(self, canal: discord.TextChannel, dono: discord.Member):
        super().__init__(timeout=None)
        self.canal = canal
        self.dono = dono

    @discord.ui.button(label="🗑️ Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_deletar_ticket")
    async def btn_deletar(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(CARGO_STAFF_ID)
        is_staff = staff_role in interaction.user.roles if staff_role else False
        if not is_staff:
            await interaction.response.send_message("❌ Apenas staff pode fechar este ticket.", ephemeral=True)
            return
        await interaction.response.send_modal(ModalConfirmarDelete(self.canal, self.dono))