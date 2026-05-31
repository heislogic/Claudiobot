import discord
from discord.ext import commands
from config import CATEGORIAS_POR_CLASSE, EMOJIS_POR_CLASSE, BUILD_LEADER_POR_CLASSE, CARGO_STAFF_ID
from database import db
from views.ticket_views import ViewDeletarTicket

async def criar_ticket(interaction: discord.Interaction, usuario: discord.Member, nickname: str, classe: str):
    """Cria o canal de ticket e salva no banco de dados."""
    try:
        classe_normalizada = classe.strip().upper()
        categoria_id = CATEGORIAS_POR_CLASSE.get(classe_normalizada)
        if not categoria_id:
            await interaction.followup.send(
                f"⚠️ Classe `{classe}` inválida. Categorias disponíveis: DPS, HEALER, TANK.\n"
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

        nome_sanitizado = ''.join(c if c.isalnum() or c == '-' else '-' for c in nickname.lower())
        nome_sanitizado = nome_sanitizado.replace(' ', '-')
        nome_canal = f"{emoji}・{nome_sanitizado}"

        # Verificar duplicidade
        for canal_existente in interaction.guild.text_channels:
            if canal_existente.name == nome_canal and canal_existente.category_id == categoria_id:
                await interaction.followup.send(
                    f"⚠️ Já existe um canal com o nome `{nome_canal}` nesta categoria.",
                    ephemeral=True
                )
                return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            usuario: discord.PermissionOverwrite(
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
            title=f"{emoji} Canal de Build - {nickname}",
            description=(
                f"Bem-vindo(a) {usuario.mention}!\n\n"
                "Este canal é destinado à **análise de builds** pelos nossos Build Leaders.\n"
                "Envie aqui suas configurações de equipamentos, talentos e dúvidas.\n\n"
                "Staff e BL's irão te auxiliar para otimizar sua build."
            ),
            color=discord.Color.green()
        )
        view_deletar = ViewDeletarTicket(canal_privado, usuario)
        msg_boas_vindas = await canal_privado.send(embed=embed_canal, view=view_deletar)

        db.adicionar_ticket_ativo(
            channel_id=canal_privado.id,
            dono_id=usuario.id,
            message_id=msg_boas_vindas.id
        )

        try:
            await usuario.send(f"✅ Seu canal de build foi criado na categoria {categoria.name}: {canal_privado.mention}")
        except discord.Forbidden:
            pass

        await interaction.followup.send("✅ Canal criado com sucesso!", ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send("⚠️ Sem permissão para criar canal. Verifique as permissões do bot.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erro ao criar canal: {str(e)}", ephemeral=True)

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(TicketCog(bot))