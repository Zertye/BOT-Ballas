import discord
import io
import datetime
from discord.ext import commands
from discord import app_commands

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors, GUILD_ID


async def generate_transcript(channel: discord.TextChannel) -> io.StringIO:
    lines = [f"TRANSCRIPT — {channel.name}", f"Date : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", "-" * 50, ""]
    async for msg in channel.history(limit=None, oldest_first=True):
        ts = msg.created_at.strftime('%d/%m %H:%M')
        content = msg.content + (f" [Fichier: {msg.attachments[0].url}]" if msg.attachments else "")
        lines.append(f"[{ts}] {msg.author.name}: {content}")
    return io.StringIO("\n".join(lines))


class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        titles = {"autre": "Autre demande", "rdv": "Demande de RDV", "achat": "Demande d'achat"}
        super().__init__(title=titles.get(ticket_type, "Nouveau ticket"))
        self.ticket_type = ticket_type

        if ticket_type == "autre":
            self.add_item(discord.ui.TextInput(label="Pseudo RP", placeholder="Ton pseudo en jeu", required=True))
            self.add_item(discord.ui.TextInput(label="Ta demande", style=discord.TextStyle.long, required=True))
        elif ticket_type == "rdv":
            self.add_item(discord.ui.TextInput(label="Pseudo RP", placeholder="Ton pseudo en jeu", required=True))
            self.add_item(discord.ui.TextInput(label="Objet du RDV", placeholder="Pourquoi veux-tu un RDV ?", required=True))
            self.add_item(discord.ui.TextInput(label="Disponibilités", style=discord.TextStyle.long, placeholder="Quand es-tu disponible ?", required=True))
        elif ticket_type == "achat":
            self.add_item(discord.ui.TextInput(label="Pseudo RP", placeholder="Ton pseudo en jeu", required=True))
            self.add_item(discord.ui.TextInput(label="Article souhaité", placeholder="Que veux-tu acheter ?", required=True))
            self.add_item(discord.ui.TextInput(label="Quantité", placeholder="Combien ?", required=True, max_length=10))
            self.add_item(discord.ui.TextInput(label="Informations complémentaires", style=discord.TextStyle.long, required=False))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CHANNELS["tickets_category"])
        staff_role = guild.get_role(ROLES["support"])
        
        if not category or not staff_role:
            return await interaction.followup.send("❌ Erreur de configuration.", ephemeral=True)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        }
        
        channel = await guild.create_text_channel(name=f"{self.ticket_type}-{user.name.lower()[:20]}", category=category, overwrites=overwrites, topic=f"Propriétaire: {user.id} | Type: {self.ticket_type}")
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name=self.title, icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"Yo {user.mention}, un membre du gang va te répondre."
        for c in self.children:
            if hasattr(c, 'value') and c.value:
                embed.add_field(name=str(c.label), value=c.value, inline=False)
        embed.set_footer(text="Ballas — RMB RP")
        
        await channel.send(content=f"{staff_role.mention} {user.mention}", embed=embed, view=TicketManagementView())
        await interaction.followup.send(f"✅ Ticket créé : {channel.mention}", ephemeral=True)


class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    def _staff(self, i):
        r = i.guild.get_role(ROLES["support"])
        return r in i.user.roles if r else False

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.success, custom_id="ticket_claim_ballas")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._staff(interaction):
            return await interaction.response.send_message("❌ Réservé au gang.", ephemeral=True)
        embed = interaction.message.embeds[0]
        if "Pris en charge" in (embed.footer.text or ""):
            return await interaction.response.send_message("Déjà pris en charge.", ephemeral=True)
        embed.set_footer(text=f"Pris en charge par {interaction.user.display_name}")
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"✅ {interaction.user.mention} prend en charge ce ticket.")

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, custom_id="ticket_close_ballas")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._staff(interaction):
            return await interaction.response.send_message("❌ Réservé au gang.", ephemeral=True)
        await interaction.response.send_message("Générer un transcript ?", view=CloseConfirmView(), ephemeral=True)

    @discord.ui.button(label="Ajouter membre", style=discord.ButtonStyle.secondary, custom_id="ticket_add_ballas")
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._staff(interaction):
            return await interaction.response.send_message("❌ Réservé au gang.", ephemeral=True)
        await interaction.response.send_message("Qui ajouter ?", view=AddMemberView(), ephemeral=True)


class AddMemberView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Membre à ajouter", min_values=1, max_values=1)
    async def select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        m = select.values[0]
        await interaction.channel.set_permissions(m, view_channel=True, send_messages=True)
        await interaction.response.edit_message(content=f"✅ {m.mention} ajouté.", view=None)


class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Avec transcript", style=discord.ButtonStyle.primary, custom_id="close_with_transcript_ballas")
    async def with_t(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close(interaction, True)

    @discord.ui.button(label="Sans transcript", style=discord.ButtonStyle.secondary, custom_id="close_no_transcript_ballas")
    async def without_t(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close(interaction, False)
    
    async def _close(self, interaction, transcript):
        await interaction.response.edit_message(content="⏳ Fermeture...", view=None)
        channel = interaction.channel
        guild = interaction.guild
        
        user = None
        try:
            if channel.topic:
                user = guild.get_member(int(channel.topic.split("Propriétaire: ")[1].split(" |")[0]))
        except: pass
        
        file = None
        if transcript:
            f = await generate_transcript(channel)
            file = discord.File(f, filename=f"transcript-{channel.name}.txt")
        
        log = guild.get_channel(CHANNELS["tickets_logs"])
        if log:
            embed = discord.Embed(color=Colors.MUTED, description=f"**{channel.name}**\nFermé par {interaction.user.mention}", timestamp=datetime.datetime.now())
            embed.set_author(name="📁 Ticket fermé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            if file:
                file.fp.seek(0)
                await log.send(embed=embed, file=file)
            else:
                await log.send(embed=embed)
        
        if user:
            try:
                embed = discord.Embed(color=EMBED_COLOR, description="Ton ticket a été fermé. Merci !")
                embed.set_author(name="Ticket fermé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if file:
                    file.fp.seek(0)
                    await user.send(embed=embed, file=discord.File(file.fp, filename=f"transcript-{channel.name}.txt"))
                else:
                    await user.send(embed=embed)
            except: pass
        
        await channel.delete()


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(placeholder="Choisir une catégorie", custom_id="main_ticket_select_ballas", options=[
        discord.SelectOption(label="Rendez-vous", value="rdv", emoji="📅", description="Demander un RDV"),
        discord.SelectOption(label="Achat", value="achat", emoji="💰", description="Acheter un produit"),
        discord.SelectOption(label="Autre", value="autre", emoji="💬", description="Autre demande")
    ])
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        await interaction.response.send_modal(TicketModal(val))


class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Installer le panneau de tickets"""
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="💜 Services Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "Sélectionne une catégorie pour ouvrir un ticket.\n\n📅 **Rendez-vous** · Prendre un RDV\n💰 **Achat** · Acheter un produit\n💬 **Autre** · Autre demande"
        if BANNER_URL and BANNER_URL != "a config":
            embed.set_thumbnail(url=BANNER_URL)
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.channel.send(embed=embed, view=TicketPanelView())
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
