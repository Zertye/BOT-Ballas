import discord
from discord.ext import commands

import sys
sys.path.append("..")
from config import GUILD_ID, CHANNELS, EMBED_COLOR, LOGO_URL, BANNER_URL

WELCOME_ID = CHANNELS.get("welcome")
PROJECT_ID = CHANNELS.get("project")
REG_ID = CHANNELS.get("registration")


class WelcomeButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Projet", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{GUILD_ID}/{PROJECT_ID}"))
        self.add_item(discord.ui.Button(label="S'enregistrer", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{GUILD_ID}/{REG_ID}"))


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(WELCOME_ID)
        if not channel:
            return
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="💜 Bienvenue chez les Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = (
            "Yo ! Bienvenue parmi nous !\n\n"
            "Pour commencer, pense à t'enregistrer pour accéder à l'ensemble du serveur."
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if BANNER_URL and BANNER_URL != "a config":
            embed.set_image(url=BANNER_URL)
        embed.set_footer(text=f"Membre #{member.guild.member_count} · Ballas — RMB RP")
        
        await channel.send(content=f"Yo {member.mention} ! 💜", embed=embed, view=WelcomeButtons())
        
        try:
            dm = discord.Embed(color=EMBED_COLOR)
            dm.set_author(name="💜 Bienvenue !", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            dm.description = f"Pour accéder au serveur, enregistre-toi ici :\nhttps://discord.com/channels/{GUILD_ID}/{REG_ID}"
            dm.set_footer(text="Ballas — RMB RP")
            await member.send(embed=dm)
        except: pass

    @commands.command(name="welcome")
    @commands.has_permissions(administrator=True)
    async def test(self, ctx, member: discord.Member = None):
        """Tester le message de bienvenue"""
        await self.on_member_join(member or ctx.author)
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(Welcome(bot))
