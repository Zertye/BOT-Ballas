import discord
from discord.ext import commands
from discord import app_commands

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors

STAFF_VALIDATION_CHANNEL_ID = CHANNELS.get("grade_requests")


class RegistrationModal(discord.ui.Modal, title="Enregistrement"):
    nom = discord.ui.TextInput(label="Nom", placeholder="Dupont")
    prenom = discord.ui.TextInput(label="Prénom", placeholder="Jean")
    id_game = discord.ui.TextInput(label="ID en jeu", placeholder="0", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.id_game.value.isdigit():
            return await interaction.response.send_message("❌ L'ID doit être un nombre.", ephemeral=True)
        
        channel = interaction.guild.get_channel(STAFF_VALIDATION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("❌ Erreur de configuration.", ephemeral=True)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="Nouvelle demande d'enregistrement", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Identité", value=f"{self.nom.value.capitalize()} {self.prenom.value.capitalize()}", inline=True)
        embed.add_field(name="ID", value=self.id_game.value, inline=True)
        embed.add_field(name="Discord", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"{interaction.user.id}|{self.nom.value}|{self.prenom.value}|{self.id_game.value}")
        
        await channel.send(embed=embed, view=ValidationView())
        await interaction.response.send_message("✅ Demande envoyée aux hauts-gradés.", ephemeral=True)


class ValidationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, custom_id="reg_accept_ballas")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            meta = interaction.message.embeds[0].footer.text.split("|")
            user_id, nom, prenom, id_game = int(meta[0]), meta[1].capitalize(), meta[2].capitalize(), meta[3]
        except:
            return await interaction.response.send_message("❌ Erreur données.", ephemeral=True)
        
        member = interaction.guild.get_member(user_id)
        if not member:
            return await interaction.response.send_message("❌ Membre parti.", ephemeral=True)
        
        nick = f"{nom} {prenom} | {id_game}"
        try: await member.edit(nick=nick)
        except: pass
        
        role = interaction.guild.get_role(ROLES.get("citoyen"))
        if role:
            try: await member.add_roles(role)
            except: pass
        
        embed = interaction.message.embeds[0]
        embed.color = Colors.SUCCESS
        embed.set_author(name="✅ Validé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="Par", value=interaction.user.mention)
        for c in self.children: c.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✅ {nick} enregistré.", ephemeral=True)
        
        try:
            dm = discord.Embed(color=Colors.SUCCESS, description=f"Ton identité **{nick}** a été validée !")
            dm.set_author(name="✅ Enregistrement validé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            await member.send(embed=dm)
        except: pass

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, custom_id="reg_refuse_ballas")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_id = int(interaction.message.embeds[0].footer.text.split("|")[0])
        except:
            return await interaction.response.send_message("❌ Erreur données.", ephemeral=True)
        
        embed = interaction.message.embeds[0]
        embed.color = Colors.ERROR
        embed.set_author(name="❌ Refusé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="Par", value=interaction.user.mention)
        for c in self.children: c.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("Refusé.", ephemeral=True)
        
        member = interaction.guild.get_member(user_id)
        if member:
            try:
                dm = discord.Embed(color=Colors.ERROR, description="Ta demande a été refusée. Vérifie tes informations.")
                dm.set_author(name="Enregistrement refusé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                await member.send(embed=dm)
            except: pass


class RegisterButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'enregistrer", style=discord.ButtonStyle.primary, custom_id="start_registration_ballas")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationModal())


class RegistrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_registration")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Installer le panneau d'enregistrement"""
        embed = discord.Embed(color=EMBED_COLOR, description="Clique ci-dessous pour t'enregistrer.")
        embed.set_author(name="📋 Enregistrement", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        if BANNER_URL and BANNER_URL != "a config":
            embed.set_thumbnail(url=BANNER_URL)
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.channel.send(embed=embed, view=RegisterButtonView())
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(RegistrationCog(bot))
