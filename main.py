import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CANAL_STAFF_ID = 1509687523268493510
CATEGORIA_MEMBROS_ID = 1450345042668556295
CARGO_STAFF_ID = 1450345042202853408

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} está na rede!")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar: {e}")

# --- Modal do formulário ---
class FormularioAlistamento(discord.ui.Modal, title="🥷 Wanted Formulário 🥷"):
    nickname = discord.ui.TextInput(label="Nickname", placeholder="Seu nickname in-game", required=True, max_length=32)
    classe = discord.ui.TextInput(label="Classe", placeholder="Ex: DPS, TANK, HEALER", required=True, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        canal_staff = interaction.client.get_channel(CANAL_STAFF_ID)
        if canal_staff:
            embed = discord.Embed(title="📋 Formulário enviado", color=discord.Color.orange())
            embed.add_field(name="Usuario", value=interaction.user.mention, inline=False)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="Classe", value=self.classe.value, inline=True)
            embed.set_footer(text=f"ID: {interaction.user.id}")
            view = ViewStaff(interaction.user, self.nickname.value, self.classe.value)
            await canal_staff.send(content=f"<@&{CARGO_STAFF_ID}> novo formulário enviado por {interaction.user.mention}!", embed=embed, view=view)
        await interaction.response.send_message("✅ Formulário enviado! Aguarde a análise da staff.", ephemeral=True)

# --- Modal de recusa ---
class ModalRecusa(discord.ui.Modal, title="❌ Formulário Recusado ❌"):
    motivo = discord.ui.TextInput(label="Motivo", placeholder="Explique o motivo da recusa", required=True, max_length=500)
    def __init__(self, usuario: discord.Member, classe: str):
        super().__init__()
        self.usuario = usuario
        self.classe = classe
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.usuario.send(f"❌ Seu alistamento para **Wanted** foi recusado.\n**Motivo:** {self.motivo.value}")
        except discord.Forbidden:
            pass
        await interaction.response.send_message(f"Recusado! {self.usuario.mention} foi notificado.", ephemeral=True)

# --- Modal de confirmação para deletar canal ---
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
        # Defer pois deletar canal pode demorar
        await interaction.response.defer(ephemeral=True)
        # Salva informações antes de deletar
        nome_canal = self.canal.name
        dono = self.dono
        # Deleta o canal
        try:
            await self.canal.delete()
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Sem permissão para deletar este canal.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"⚠️ Erro ao deletar: {str(e)}", ephemeral=True)
            return
        # Notifica o dono via DM
        try:
            await dono.send(f"🗑️ Seu canal `{nome_canal}` foi deletado por {interaction.user.mention}.")
        except:
            pass
        # Notifica a staff (opcional)
        canal_staff = interaction.guild.get_channel(CANAL_STAFF_ID)
        if canal_staff:
            await canal_staff.send(f"🗑️ Canal `{nome_canal}` deletado por {interaction.user.mention} (dono: {dono.mention})")
        await interaction.followup.send("✅ Canal deletado com sucesso!", ephemeral=True)

# --- View do botão de deletar canal (dentro do ticket) ---
class ViewDeletarTicket(discord.ui.View):
    def __init__(self, canal: discord.TextChannel, dono: discord.Member):
        super().__init__(timeout=None)
        self.canal = canal
        self.dono = dono

    @discord.ui.button(label="🗑️ Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_deletar_ticket")
    async def btn_deletar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica permissão: dono ou staff (cargo staff)
        staff_role = interaction.guild.get_role(CARGO_STAFF_ID)
        is_staff = staff_role in interaction.user.roles
        if interaction.user.id != self.dono.id and not is_staff:
            await interaction.response.send_message("❌ Você não tem permissão para deletar este canal.", ephemeral=True)
            return
        # Abre modal de confirmação
        await interaction.response.send_modal(ModalConfirmarDelete(self.canal, self.dono))

# --- View dos botões de staff (aceitar/recusar formulário) ---
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

        # Criação do canal privado
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_MEMBROS_ID)
            if not categoria:
                raise Exception("Categoria não encontrada.")
            nome_sanitizado = ''.join(c if c.isalnum() or c == '-' else '-' for c in self.nickname.lower())
            nome_sanitizado = nome_sanitizado.replace(' ', '-')
            nome_canal = f"{self.classe.lower()}-{nome_sanitizado}"

            canal_privado = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,
                overwrites={
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    self.usuario: discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, read_message_history=True, attach_files=True
                    ),
                    interaction.guild.get_role(CARGO_STAFF_ID): discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, read_message_history=True, manage_channels=True
                    ),
                    interaction.guild.me: discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_channels=True
                    )
                }
            )

            embed_canal = discord.Embed(
                title="📁 Canal de Build",
                description=(
                    f"Bem-vindo(a) {self.usuario.mention}!\n\n"
                    "Este canal é destinado à **análise de builds** pelos nossos especialistas.\n"
                    "Envie aqui suas configurações de equipamentos, talentos e dúvidas.\n\n"
                    "Staff e analistas irão te auxiliar para otimizar seu personagem."
                ),
                color=discord.Color.green()
            )
            # Envia a mensagem de boas-vindas COM o botão de deletar
            view_deletar = ViewDeletarTicket(canal_privado, self.usuario)
            await canal_privado.send(embed=embed_canal, view=view_deletar)

            await self.usuario.send(f"✅ Seu canal de build foi criado: {canal_privado.mention}")

        except Exception as e:
            await interaction.followup.send(f"⚠️ Cargo e nickname aplicados, mas erro ao criar canal: {str(e)}", ephemeral=True)

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="btn_recusar")
    async def btn_recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRecusa(self.usuario, self.classe))
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

# --- View com botão para abrir formulário ---
class ViewFormulario(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Preencher Formulário", style=discord.ButtonStyle.green, custom_id="btn_formulario")
    async def btn_formulario(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FormularioAlistamento())

# --- Comando /formulario ---
@bot.tree.command(name="formulario", description="formulario")
@commands.has_permissions(administrator=True)
async def formulario(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🥷 Wanted Formulário 🥷",
        description="Deseja entrar na Wanted? Clique no botão abaixo para preencher o formulário.",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=ViewFormulario())
    await interaction.response.send_message("Formulário enviado!", ephemeral=True)

bot.run(TOKEN)