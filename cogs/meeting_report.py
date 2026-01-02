import discord
from discord.ext import commands
from discord import app_commands
import datetime

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, Colors, CHANNELS, ROLES

# === CONFIGURATION ===
REPORT_PANEL_CHANNEL = CHANNELS.get("meeting_report")
ANNOUNCEMENT_CHANNEL = CHANNELS.get("announcements")
VALIDATOR_ROLE = ROLES.get("report_validator")


class MeetingReportData:
    """Stocke temporairement les données d'un compte rendu en cours de création"""
    def __init__(self, author: discord.Member):
        self.author = author
        self.report_title: str = ""
        self.attendees: list[discord.Member] = []
        self.promotions: list[dict] = []
        self.reminders: str = ""
        self.other_content: str = ""


# Stockage temporaire des rapports en cours (user_id -> MeetingReportData)
pending_reports: dict[int, MeetingReportData] = {}


def format_report_embed(data: MeetingReportData, preview: bool = False) -> discord.Embed:
    """Formate le compte rendu en embed"""
    embed = discord.Embed(color=EMBED_COLOR)
    
    if preview:
        embed.set_author(name="📋 Compte Rendu — En attente de validation", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    else:
        embed.set_author(name="📋 Compte Rendu de Réunion", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    
    if data.report_title:
        embed.description = f"```{data.report_title}```"
    
    if data.attendees:
        attendees_str = ", ".join([m.mention for m in data.attendees])
        embed.add_field(name="👔 Hauts-Gradés présents", value=attendees_str, inline=False)
    
    if data.promotions:
        promo_lines = []
        retro_lines = []
        
        for p in data.promotions:
            line = f"• {p['member'].mention} : {p['old_role'].mention} → {p['new_role'].mention}"
            if p['type'] == "promotion":
                promo_lines.append(line)
            else:
                retro_lines.append(line)
        
        if promo_lines:
            embed.add_field(name="📈 Promotions", value="\n".join(promo_lines), inline=False)
        if retro_lines:
            embed.add_field(name="📉 Rétrogradations", value="\n".join(retro_lines), inline=False)
    
    if data.reminders:
        embed.add_field(name="🔔 Rappels", value=data.reminders, inline=False)
    
    if data.other_content:
        embed.add_field(name="📝 Informations complémentaires", value=data.other_content, inline=False)
    
    embed.set_footer(text=f"Rédigé par {data.author.display_name} · Ballas — RMB RP")
    
    if BANNER_URL and BANNER_URL != "a config":
        embed.set_thumbnail(url=LOGO_URL if LOGO_URL != "a config" else None)
    
    return embed


class ReportPanelView(discord.ui.View):
    """Vue principale du panneau de création"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un compte rendu", style=discord.ButtonStyle.primary, emoji="📝", custom_id="meeting_report_create_ballas")
    async def create_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        pending_reports[interaction.user.id] = MeetingReportData(interaction.user)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📋 Nouveau Compte Rendu", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "**Étape 1/4** — Sélectionne les hauts-gradés présents."
        embed.set_footer(text="Ballas — RMB RP")
        
        await interaction.response.send_message(embed=embed, view=AttendeeSelectView(), ephemeral=True)


class AttendeeSelectView(discord.ui.View):
    """Étape 1 : Sélection des présents"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Sélectionner les présents", min_values=1, max_values=25, custom_id="attendee_select")
    async def select_attendees(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée, recommence.", ephemeral=True)
        
        pending_reports[interaction.user.id].attendees = list(select.values)
        await interaction.response.defer()

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.success, emoji="➡️", row=2)
    async def next_step(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée, recommence.", ephemeral=True)
        
        data = pending_reports[interaction.user.id]
        if not data.attendees:
            return await interaction.response.send_message("❌ Sélectionne au moins un présent.", ephemeral=True)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📋 Nouveau Compte Rendu", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = (
            "**Étape 2/4** — Promotions & Rétrogradations\n\n"
            "Utilise les boutons pour ajouter des changements de grade.\n"
            "Clique sur **Suivant** quand tu as terminé (optionnel)."
        )
        
        if data.promotions:
            lines = []
            for p in data.promotions:
                emoji = "📈" if p['type'] == "promotion" else "📉"
                lines.append(f"{emoji} {p['member'].display_name} : {p['old_role'].name} → {p['new_role'].name}")
            embed.add_field(name="Changements ajoutés", value="\n".join(lines), inline=False)
        
        embed.set_footer(text="Ballas — RMB RP")
        
        await interaction.response.edit_message(embed=embed, view=PromotionView())

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in pending_reports:
            del pending_reports[interaction.user.id]
        await interaction.response.edit_message(content="❌ Compte rendu annulé.", embed=None, view=None)


class PromotionView(discord.ui.View):
    """Étape 2 : Gestion des promotions/rétrogradations"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Ajouter une promotion", style=discord.ButtonStyle.success, emoji="📈", row=0)
    async def add_promotion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        embed = discord.Embed(color=Colors.SUCCESS)
        embed.set_author(name="📈 Nouvelle Promotion", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "Sélectionne le membre à promouvoir."
        
        await interaction.response.send_message(embed=embed, view=MemberSelectForPromoView("promotion"), ephemeral=True)

    @discord.ui.button(label="Ajouter une rétrogradation", style=discord.ButtonStyle.danger, emoji="📉", row=0)
    async def add_retrogradation(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        embed = discord.Embed(color=Colors.ERROR)
        embed.set_author(name="📉 Nouvelle Rétrogradation", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "Sélectionne le membre à rétrograder."
        
        await interaction.response.send_message(embed=embed, view=MemberSelectForPromoView("retrogradation"), ephemeral=True)

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.primary, emoji="➡️", row=1)
    async def next_step(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        await interaction.response.send_modal(ContentModal())

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="❌", row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in pending_reports:
            del pending_reports[interaction.user.id]
        await interaction.response.edit_message(content="❌ Compte rendu annulé.", embed=None, view=None)


class MemberSelectForPromoView(discord.ui.View):
    """Sélection du membre pour promotion/rétrogradation"""
    def __init__(self, promo_type: str):
        super().__init__(timeout=120)
        self.promo_type = promo_type
        self.selected_member = None

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Choisir le membre", min_values=1, max_values=1)
    async def select_member(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_member = select.values[0]
        
        embed = discord.Embed(color=Colors.SUCCESS if self.promo_type == "promotion" else Colors.ERROR)
        emoji = "📈" if self.promo_type == "promotion" else "📉"
        embed.set_author(name=f"{emoji} {self.promo_type.capitalize()}", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"Membre : **{self.selected_member.display_name}**\n\nSélectionne l'**ancien grade** (grade actuel)."
        
        await interaction.response.edit_message(embed=embed, view=OldRoleSelectView(self.promo_type, self.selected_member))


class OldRoleSelectView(discord.ui.View):
    """Sélection de l'ancien rôle"""
    def __init__(self, promo_type: str, member: discord.Member):
        super().__init__(timeout=120)
        self.promo_type = promo_type
        self.member = member
        self.old_role = None

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Ancien grade (actuel)", min_values=1, max_values=1)
    async def select_old_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.old_role = select.values[0]
        
        embed = discord.Embed(color=Colors.SUCCESS if self.promo_type == "promotion" else Colors.ERROR)
        emoji = "📈" if self.promo_type == "promotion" else "📉"
        embed.set_author(name=f"{emoji} {self.promo_type.capitalize()}", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"Membre : **{self.member.display_name}**\nAncien grade : {self.old_role.mention}\n\nSélectionne le **nouveau grade**."
        
        await interaction.response.edit_message(embed=embed, view=NewRoleSelectView(self.promo_type, self.member, self.old_role))


class NewRoleSelectView(discord.ui.View):
    """Sélection du nouveau rôle"""
    def __init__(self, promo_type: str, member: discord.Member, old_role: discord.Role):
        super().__init__(timeout=120)
        self.promo_type = promo_type
        self.member = member
        self.old_role = old_role

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Nouveau grade", min_values=1, max_values=1)
    async def select_new_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        new_role = select.values[0]
        
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        pending_reports[interaction.user.id].promotions.append({
            "member": self.member,
            "old_role": self.old_role,
            "new_role": new_role,
            "type": self.promo_type
        })
        
        emoji = "📈" if self.promo_type == "promotion" else "📉"
        embed = discord.Embed(color=Colors.SUCCESS)
        embed.set_author(name=f"✅ {self.promo_type.capitalize()} ajoutée", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"{emoji} **{self.member.display_name}**\n{self.old_role.mention} → {new_role.mention}"
        embed.set_footer(text="Ferme ce message et continue la création.")
        
        await interaction.response.edit_message(embed=embed, view=None)


class ContentModal(discord.ui.Modal, title="Contenu du compte rendu"):
    """Étape 3 : Titre, Rappels et contenu"""
    report_title = discord.ui.TextInput(
        label="Titre du compte rendu",
        style=discord.TextStyle.short,
        placeholder="Réunion Hebdomadaire Hauts-Gradés",
        required=True,
        max_length=100
    )
    reminders = discord.ui.TextInput(
        label="Rappels globaux",
        style=discord.TextStyle.long,
        placeholder="Les rappels importants pour le gang...",
        required=False,
        max_length=1000
    )
    other = discord.ui.TextInput(
        label="Autres informations",
        style=discord.TextStyle.long,
        placeholder="Autres points abordés, décisions, etc...",
        required=False,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        data = pending_reports[interaction.user.id]
        data.report_title = self.report_title.value or ""
        data.reminders = self.reminders.value or ""
        data.other_content = self.other.value or ""
        
        embed = format_report_embed(data, preview=True)
        
        preview_embed = discord.Embed(color=Colors.WARNING)
        preview_embed.set_author(name="👁️ Prévisualisation", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        preview_embed.description = "Voici ton compte rendu. Vérifie et envoie pour validation."
        
        await interaction.response.edit_message(embed=preview_embed, view=None)
        await interaction.followup.send(embed=embed, view=PreviewConfirmView(), ephemeral=True)


class PreviewConfirmView(discord.ui.View):
    """Étape 4 : Confirmation avant envoi"""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Envoyer pour validation", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in pending_reports:
            return await interaction.response.send_message("❌ Session expirée.", ephemeral=True)
        
        data = pending_reports[interaction.user.id]
        channel = interaction.guild.get_channel(REPORT_PANEL_CHANNEL)
        
        if not channel:
            return await interaction.response.send_message("❌ Salon de validation introuvable.", ephemeral=True)
        
        embed = format_report_embed(data, preview=True)
        
        validator_role = interaction.guild.get_role(VALIDATOR_ROLE) if VALIDATOR_ROLE and VALIDATOR_ROLE != "a config" else None
        content = f"{validator_role.mention if validator_role else ''} Nouveau compte rendu à valider de {interaction.user.mention}"
        
        embed.set_footer(text=f"Auteur: {interaction.user.id} · Ballas — RMB RP")
        
        bot = interaction.client
        msg = await channel.send(content=content, embed=embed, view=ReportValidationView())
        
        if bot.pool:
            async with bot.pool.acquire() as conn:
                attendees_ids = ",".join([str(m.id) for m in data.attendees])
                promotions_data = ";".join([
                    f"{p['member'].id},{p['old_role'].id},{p['new_role'].id},{p['type']}"
                    for p in data.promotions
                ])
                
                await conn.execute("""
                    INSERT INTO meeting_reports (message_id, author_id, report_title, attendees, promotions, reminders, other_content)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, msg.id, interaction.user.id, data.report_title, attendees_ids, promotions_data, data.reminders, data.other_content)
        
        del pending_reports[interaction.user.id]
        
        await interaction.response.edit_message(
            content=f"✅ Compte rendu envoyé pour validation dans {channel.mention}",
            embed=None,
            view=None
        )

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in pending_reports:
            del pending_reports[interaction.user.id]
        await interaction.response.edit_message(content="❌ Compte rendu annulé.", embed=None, view=None)


class ReportValidationView(discord.ui.View):
    """Vue de validation (persistante)"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Valider", style=discord.ButtonStyle.success, emoji="✅", custom_id="meeting_report_validate_ballas")
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
        validator_role = interaction.guild.get_role(VALIDATOR_ROLE) if VALIDATOR_ROLE and VALIDATOR_ROLE != "a config" else None
        if validator_role and validator_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Tu n'as pas la permission de valider.", ephemeral=True)
        
        await interaction.response.defer()
        
        announcement_channel = interaction.guild.get_channel(ANNOUNCEMENT_CHANNEL)
        if not announcement_channel:
            return await interaction.followup.send("❌ Salon d'annonces introuvable.", ephemeral=True)
        
        original_embed = interaction.message.embeds[0]
        
        footer_text = original_embed.footer.text if original_embed.footer else ""
        author_id = None
        if "Auteur:" in footer_text:
            try:
                author_id = int(footer_text.split("Auteur:")[1].split("·")[0].strip())
            except:
                pass
        
        author = interaction.guild.get_member(author_id) if author_id else None
        
        final_embed = discord.Embed(color=EMBED_COLOR)
        final_embed.set_author(name="📋 Compte Rendu de Réunion", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        
        if original_embed.description:
            final_embed.description = original_embed.description
        
        for field in original_embed.fields:
            final_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        final_embed.set_footer(text=f"Rédigé par {author.display_name if author else 'Les Hauts-Gradés'} · Ballas — RMB RP")
        
        if BANNER_URL and BANNER_URL != "a config":
            final_embed.set_thumbnail(url=LOGO_URL if LOGO_URL != "a config" else None)
        
        await announcement_channel.send(content="@everyone", embed=final_embed)
        
        bot = interaction.client
        if bot.pool:
            async with bot.pool.acquire() as conn:
                await conn.execute("DELETE FROM meeting_reports WHERE message_id = $1", interaction.message.id)
        
        validated_embed = discord.Embed(color=Colors.SUCCESS)
        validated_embed.set_author(name="✅ Compte rendu validé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        validated_embed.description = f"Validé par {interaction.user.mention}\nAnnonce publiée dans {announcement_channel.mention}"
        validated_embed.set_footer(text="Ballas — RMB RP")
        
        await interaction.message.edit(content=None, embed=validated_embed, view=None)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, emoji="❌", custom_id="meeting_report_refuse_ballas")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        validator_role = interaction.guild.get_role(VALIDATOR_ROLE) if VALIDATOR_ROLE and VALIDATOR_ROLE != "a config" else None
        if validator_role and validator_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Tu n'as pas la permission de refuser.", ephemeral=True)
        
        bot = interaction.client
        if bot.pool:
            async with bot.pool.acquire() as conn:
                await conn.execute("DELETE FROM meeting_reports WHERE message_id = $1", interaction.message.id)
        
        await interaction.message.delete()
        await interaction.response.send_message("🗑️ Compte rendu refusé et supprimé.", ephemeral=True)


async def recreate_report_panel(bot):
    """Supprime et recrée le panneau de création (utilisé par setup_all)"""
    channel = bot.get_channel(REPORT_PANEL_CHANNEL)
    if not channel:
        return
    
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            embed = msg.embeds[0]
            if embed.author and "Créer un Compte Rendu" in (embed.author.name or ""):
                await msg.delete()
                break
    
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name="📝 Créer un Compte Rendu", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    embed.description = (
        "Clique sur le bouton ci-dessous pour créer un nouveau compte rendu de réunion.\n\n"
        "**Étapes :**\n"
        "1️⃣ Sélectionner les hauts-gradés présents\n"
        "2️⃣ Ajouter promotions/rétrogradations\n"
        "3️⃣ Titre, rappels et informations\n"
        "4️⃣ Envoyer pour validation"
    )
    if BANNER_URL and BANNER_URL != "a config":
        embed.set_thumbnail(url=BANNER_URL)
    embed.set_footer(text="Ballas — RMB RP")
    
    await channel.send(embed=embed, view=ReportPanelView())


class MeetingReportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Initialiser la table en BDD au chargement"""
        if self.bot.pool:
            async with self.bot.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS meeting_reports (
                        id SERIAL PRIMARY KEY,
                        message_id BIGINT UNIQUE NOT NULL,
                        author_id BIGINT NOT NULL,
                        report_title TEXT,
                        attendees TEXT,
                        promotions TEXT,
                        reminders TEXT,
                        other_content TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

    @commands.command(name="setup_report")
    @commands.has_permissions(administrator=True)
    async def setup_report(self, ctx):
        """Installer le panneau de compte rendu"""
        await recreate_report_panel(self.bot)
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(MeetingReportCog(bot))
