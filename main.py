import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import data_manager

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CANAL_STAFF_ID = 1509687523268493510
CARGO_STAFF_ID = 1450345042202853408

# Mapeamento de classe para ID da categoria
CATEGORIAS_POR_CLASSE = {
    "DPS": 1510032279865655387,
    "HEALER": 1510032296680362034,
    "TANK": 1510032314854408282
}

# Mapeamento de classe para emoji unicode (usado no nome do canal e embed)
EMOJIS_POR_CLASSE = {
    "DPS": "🔪",
    "HEALER": "🚑",
    "TANK": "🔰"
}

# Mapeamento de classe para ID do cargo de Build Leader
BUILD_LEADER_POR_CLASSE = {
    "DPS": 1510042154947313724,
    "HEALER": 1510042369406402580,
    "TANK": 1510042326125248534
}

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

    # --- Recuperar formulários pendentes ---
    pendentes = data_manager.listar_formularios_pendentes()
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
                    # Usuário não está mais no servidor, remover pendência
                    data_manager.remover_formulario_pendente(dados["message_id"], dados["channel_id"])
            except discord.NotFound:
                data_manager.remover_formulario_pendente(dados["message_id"], dados["channel_id"])
            except Exception as e:
                print(f"Erro ao restaurar formulário {key}: {e}")

    # --- Recuperar tickets ativos ---
    tickets = data_manager.listar_tickets_ativos()
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
                    # Dono não está mais no servidor, remover ticket
                    data_manager.remover_ticket_ativo(dados["channel_id"], dados["dono_id"])
            except discord.NotFound:
                data_manager.remover_ticket_ativo(dados["channel_id"], dados["dono_id"])
            except Exception as e:
                print(f"Erro ao restaurar ticket {key}: {e}")

# --- Modal do formulário ---
class FormularioAlistamento(discord.ui.Modal, title="🥷 Wanted Formulário 🥷"):
    nickname = discord.ui.TextInput(label="Nickname", placeholder="Seu nickname in-game", required=True, max_length=32)
    classe = discord.ui.TextInput(label="Classe", placeholder="Ex: DPS, TANK, HEALER", required=True, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        # Impedir que já membros enviem novo formulário
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
            # Salvar no JSON
            data_manager.adicionar_formulario_pendente(
                message_id=msg.id,
                channel_id=CANAL_STAFF_ID,
                user_id=interaction.user.id,
                nickname=self.nickname.value,
                classe=self.classe.value
            )
        await interaction.response.send_message("✅ Formulário enviado! Aguarde a análise da staff.", ephemeral=True)

# --- Modal de recusa ---
class ModalRecusa(discord.ui.Modal, title="❌ Formulário Recusado ❌"):
    motivo = discord.ui.TextInput(label="Motivo", placeholder="Explique o motivo da recusa", required=True, max_length=500)
    def __init__(self, usuario: discord.Member, message_id: int, channel_id: int):
        super().__init__()
        self.usuario = usuario
        self.message_id = message_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.usuario.send(
                f"❌ Seu alistamento para **Wanted** foi recusado.\n**Motivo:** {self.motivo.value}"
            )
        except discord.Forbidden:
            pass
        # Remover do JSON
        data_manager.remover_formulario_pendente(self.message_id, self.channel_id)
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

        # Remover do JSON
        data_manager.remover_ticket_ativo(self.canal.id, self.dono.id)

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

# --- View do botão de deletar canal (dentro do ticket) ---
class ViewDeletarTicket(discord.ui.View):
    def __init__(self, canal: discord.TextChannel, dono: discord.Member):
        super().__init__(timeout=None)
        self.canal = canal
        self.dono = dono

    @discord.ui.button(label="🗑️ Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="btn_deletar_ticket")
    async def btn_deletar(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(CARGO_STAFF_ID)
        is_staff = staff_role in interaction.user.roles if staff_role else False
        if interaction.user.id != self.dono.id and not is_staff:
            await interaction.response.send_message("❌ Você não tem permissão para deletar este canal.", ephemeral=True)
            return
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
        # Desabilita botões
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        # Remover formulário pendente do JSON
        data_manager.remover_formulario_pendente(interaction.message.id, interaction.channel_id)

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

        # --- CRIAÇÃO DO CANAL ---
        try:
            classe_normalizada = self.classe.strip().upper()
            categoria_id = CATEGORIAS_POR_CLASSE.get(classe_normalizada)
            if not categoria_id:
                await interaction.followup.send(
                    f"⚠️ Classe `{self.classe}` inválida. Categorias disponíveis: DPS, HEALER, TANK.\n"
                    f"Cargo e nickname aplicados, mas canal NÃO criado.",
                    ephemeral=True
                )
                return

            categoria = interaction.guild.get_channel(categoria_id)
            if not categoria:
                await interaction.followup.send(
                    f"⚠️ Categoria ID {categoria_id} para classe {classe_normalizada} não encontrada.",
                    ephemeral=True
                )
                return

            emoji = EMOJIS_POR_CLASSE.get(classe_normalizada, "📁")
            build_leader_role_id = BUILD_LEADER_POR_CLASSE.get(classe_normalizada)
            build_leader_role = interaction.guild.get_role(build_leader_role_id) if build_leader_role_id else None
            staff_role = interaction.guild.get_role(CARGO_STAFF_ID)

            nome_sanitizado = ''.join(c if c.isalnum() or c == '-' else '-' for c in self.nickname.lower())
            nome_sanitizado = nome_sanitizado.replace(' ', '-')
            nome_canal = f"{emoji}・{nome_sanitizado}"

            # Verifica duplicidade
            for canal_existente in interaction.guild.text_channels:
                if canal_existente.name == nome_canal and canal_existente.category_id == categoria_id:
                    await interaction.followup.send(
                        f"⚠️ Já existe um canal com o nome `{nome_canal}` nesta categoria.",
                        ephemeral=True
                    )
                    return

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.usuario: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True, attach_files=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_channels=True
                )
            }
            if build_leader_role:
                overwrites[build_leader_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True, attach_files=True
                )
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, read_message_history=True, manage_channels=True
                )

            canal_privado = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,
                overwrites=overwrites
            )

            embed_canal = discord.Embed(
                title=f"{emoji} Canal de Build - {self.nickname}",
                description=(
                    f"Bem-vindo(a) {self.usuario.mention}!\n\n"
                    "Este canal é destinado à **análise de builds** pelos nossos especialistas.\n"
                    "Envie aqui suas configurações de equipamentos, talentos e dúvidas.\n\n"
                    "Staff e analistas irão te auxiliar para otimizar seu personagem."
                ),
                color=discord.Color.green()
            )
            view_deletar = ViewDeletarTicket(canal_privado, self.usuario)
            msg_boas_vindas = await canal_privado.send(embed=embed_canal, view=view_deletar)

            # Salvar ticket ativo no JSON
            data_manager.adicionar_ticket_ativo(
                channel_id=canal_privado.id,
                dono_id=self.usuario.id,
                message_id=msg_boas_vindas.id
            )

            try:
                await self.usuario.send(f"✅ Seu canal de build foi criado na categoria {categoria.name}: {canal_privado.mention}")
            except discord.Forbidden:
                pass

        except discord.Forbidden:
            await interaction.followup.send("⚠️ Sem permissão para criar canal. Verifique as permissões do bot.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Cargo e nickname aplicados, mas erro ao criar canal: {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red, custom_id="btn_recusar")
    async def btn_recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRecusa(self.usuario, interaction.message.id, interaction.channel_id))
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