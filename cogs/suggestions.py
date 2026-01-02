import discord
from discord.ext import commands
from discord import app_commands
import datetime

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS

PANEL_CHANNEL_ID = CHANNELS.get("suggestions")
SUGGESTION_CHANNEL_ID = CHANNELS.get("suggestions")


class SuggestionModal(discord.ui.Modal, title="Suggestion"):
    sujet = discord.ui.TextInput(label="Sujet", placeholder="Ex: Nouvelle activité pour le gang...", max_length=100)
    contenu = discord.ui.TextInput(label="Détails", style=discord.TextStyle.long, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(SUGGESTION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("❌ Erreur de configuration.", ephemeral=True)
        
        embed = discord.Embed(color=EMBED_COLOR, description=self.contenu.value, timestamp=datetime.datetime.now())
        embed.set_author(name=f"💡 {self.sujet.value}", icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Par {interaction.user.display_name}")
        
        msg = await channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await interaction.response.send_message(f"✅ Suggestion envoyée dans {channel.mention}", ephemeral=True)


class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Faire une suggestion", style=discord.ButtonStyle.primary, emoji="💡", custom_id="ballas_suggestion_btn")
    async def suggest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_suggestions")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Installer le panneau de suggestions"""
        embed = discord.Embed(color=EMBED_COLOR, description="Une idée pour améliorer le gang ?\nPartage-la ici !")
        embed.set_author(name="💡 Boîte à idées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        if BANNER_URL and BANNER_URL != "a config":
            embed.set_thumbnail(url=BANNER_URL)
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.channel.send(embed=embed, view=SuggestionView())
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
