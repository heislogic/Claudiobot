import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# IDs dos canais e cargos
CANAL_STAFF_ID = 1509687523268493510
CATEGORIA_MEMBROS_ID = 1450345042668556295   # ID da categoria onde os canais serão criados
CARGO_STAFF_ID = 1450345042202853408         # ID do cargo da staff que terá acesso aos canais

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
    nickname = discord.ui.TextInput(
        label="Nickname",
        placeholder="Seu nickname in-game",
        required=True,
        max_length=32
    )
    classe = discord.ui.TextInput(
        label="Classe",
        placeholder="Ex: DPS, TANK, HEALER",
        required=True,
        max_length=6
    )

    async def on_submit(self, interaction: discord.Interaction):
        canal_staff = interaction.client.get_channel(CANAL_STAFF_ID)
        if canal_staff:
            embed = discord.Embed(
                title="📋 Formulário enviado",
                color=discord.Color.orange()
            )
            embed.add_field(name="Usuario", value=interaction.user.mention, inline=False)
            embed.add_field(name="Nickname", value=self.nickname.value, inline=True)
            embed.add_field(name="Classe", value=self.classe.value, inline=True)
            embed.set_footer(text=f"ID: {interaction.user.id}")

            view = ViewStaff(interaction.user, self.nickname.value, self.classe.value)
            await canal_staff.send(
                content=f"<@&{CARGO_STAFF_ID}> novo formulário enviado por {interaction.user.mention}!",
                embed=embed,
                view=view
            )

        await interaction.response.send_message(
            "✅ Formulário enviado! Aguarde a análise da staff.",
            ephemeral=True
        )

# --- Modal de recusa ---
class ModalRecusa(discord.ui.Modal, title="❌ Formulário Recusado ❌"):
    motivo = discord.ui.TextInput(
        label="Motivo",
        placeholder="Explique o motivo da recusa",
        required=True,
        max_length=500
    )

    def __init__(self, usuario: discord.Member, classe: str):
        super().__init__()
        self.usuario = usuario
        self.classe = classe

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.usuario.send(
                f"❌ Seu alistamento para **Wanted** foi recusado.\n"
                f"**Motivo:** {self.motivo.value}"
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            f"Recusado! {self.usuario.mention} foi notificado.",
            ephemeral=True
        )

# --- View dos botões de staff ---
class ViewStaff(discord.ui.View):
    def __init__(self, usuario: discord.Member, nickname: str, classe: str):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.nickname = nickname
        self.classe = classe

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.green, custom_id="btn_aceitar")
    async def btn_aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  # Defer para ações longas

        # Desabilita os botões para evitar duplicidade
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Aplica o cargo baseado na classe
        cargo = discord.utils.get(interaction.guild.roles, name=self.classe.upper())
        if cargo is None:
            await interaction.followup.send(f"⚠️ Cargo `{self.classe.upper()}` não encontrado!", ephemeral=True)
            return

        try:
            await self.usuario.add_roles(cargo)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Sem permissão para adicionar o cargo `{cargo.name}`.", ephemeral=True)
            return

        # Altera o nickname do usuário
        try:
            await self.usuario.edit(nick=self.nickname)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Cargo adicionado, mas sem permissão para alterar o nickname.", ephemeral=True)

        # --- CRIAÇÃO DO CANAL PRIVADO (build-{nickname}) ---
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_MEMBROS_ID)
            if not categoria:
                raise Exception("Categoria não encontrada. Verifique o ID.")

            # Sanitiza o nickname para nome do canal (apenas letras, números e hífen)
            nome_sanitizado = ''.join(c if c.isalnum() or c == '-' else '-' for c in self.nickname.lower())
            nome_sanitizado = nome_sanitizado.replace(' ', '-')
            nome_canal = f"build-{nome_sanitizado}"

            # Cria o canal com as permissões adequadas
            canal_privado = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,
                overwrites={
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    self.usuario: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True
                    ),
                    interaction.guild.get_role(CARGO_STAFF_ID): discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True
                    ),
                    interaction.guild.me: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_channels=True
                    )
                }
            )

            # Mensagem de boas-vindas com foco em análise de builds
            embed_canal = discord.Embed(
                title="📁 Canal de Build",
                description=(
                    f"Bem-vindo(a) {self.usuario.mention}!\n\n"
                    "Este canal é destinado à **análise de builds** pelos nossos Build Leaders.\n"
                    "Envie aqui sua build completa, talentos e dúvidas.\n\n"
                    "Staff e BL's irão te auxiliar para otimizar seu personagem."
                ),
                color=discord.Color.green()
            )
            await canal_privado.send(embed=embed_canal)

            # Notifica o usuário no privado (opcional)
            await self.usuario.send(f"✅ Seu canal de build foi criado: {canal_privado.mention}")

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Cargo e nickname aplicados, mas ocorreu erro ao criar o canal: {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="btn_recusar")
    async def btn_recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRecusa(self.usuario, self.classe))
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

# --- View com o botão para abrir formulário ---
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