import discord
from discord.ext import commands
from discord import app_commands
import asyncpg

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors

CHANNEL_ID = CHANNELS.get("tarif")
ALLOWED_ROLE_ID = ROLES.get("tarif_manager")

# Pas d'articles par défaut
DEFAULT_DATA = []

CATEGORY_CONFIG = {
    "Armes": {"emoji": "🔫", "icon": "🔫"},
    "Drogues": {"emoji": "💊", "icon": "💊"}, 
    "Véhicules": {"emoji": "🚗", "icon": "🚗"},
    "Services": {"emoji": "💼", "icon": "💼"},
    "Divers": {"emoji": "📦", "icon": "📦"}
}


def format_price(price: float) -> str:
    """Formate le prix de manière uniforme."""
    return f"{price:,.0f}$".replace(",", " ")


def build_category_block(items: list, max_name_len: int = 18) -> str:
    """Construit un bloc de code formaté pour une catégorie."""
    if not items:
        return ""
    
    lines = []
    for item in items:
        name = item['name'][:max_name_len].ljust(max_name_len)
        price = f"{float(item['price']):>8.0f}$"
        lines.append(f" {name} {price}")
    
    return "```\n" + "\n".join(lines) + "\n```"


class TariffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.init_db()

    async def init_db(self):
        if not self.bot.pool:
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ballas_catalog (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    category TEXT NOT NULL
                )
            """)

    async def update_catalog_embed(self):
        channel = self.bot.get_channel(CHANNEL_ID)
        if not channel:
            return
        
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM ballas_catalog ORDER BY category, name")
        
        cats = {"Armes": [], "Drogues": [], "Véhicules": [], "Services": [], "Divers": []}
        for r in rows:
            cats.setdefault(r['category'], []).append(r)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="💰 CATALOGUE", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        
        if BANNER_URL and BANNER_URL != "a config":
            embed.set_thumbnail(url=BANNER_URL)
        
        if not rows:
            embed.description = "*Aucun article disponible*"
        else:
            for cat in ["Armes", "Drogues", "Véhicules", "Services", "Divers"]:
                items = cats.get(cat, [])
                if not items:
                    continue
                
                config = CATEGORY_CONFIG.get(cat, {"emoji": "📦"})
                block = build_category_block(items)
                
                embed.add_field(
                    name=f"{config['emoji']}  {cat}",
                    value=block,
                    inline=False
                )
        
        total = sum(len(v) for v in cats.values())
        embed.set_footer(text=f"{total} article(s) disponible(s) • Ballas — RMB RP")
        
        try:
            async for m in channel.history(limit=10):
                if m.author == self.bot.user:
                    await m.delete()
        except:
            pass
        
        await channel.send(embed=embed)

    async def article_autocomplete(self, interaction: discord.Interaction, current: str):
        if not self.bot.pool:
            return []
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name FROM ballas_catalog WHERE name ILIKE $1 ORDER BY name LIMIT 25",
                f"%{current}%"
            )
        return [app_commands.Choice(name=r['name'], value=r['name']) for r in rows]

    @app_commands.command(name="add_article", description="Ajouter un article au catalogue")
    @app_commands.checks.has_role(ALLOWED_ROLE_ID)
    @app_commands.choices(
        category=[app_commands.Choice(name=c, value=c) for c in ["Armes", "Drogues", "Véhicules", "Services", "Divers"]]
    )
    async def add_article(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        nom: str,
        prix: float,
        description: str = None
    ):
        async with self.bot.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO ballas_catalog (name, description, price, category) VALUES ($1,$2,$3,$4)",
                    nom, description, prix, category.value
                )
            except asyncpg.UniqueViolationError:
                return await interaction.response.send_message(f"❌ **{nom}** existe déjà.", ephemeral=True)
        
        await self.update_catalog_embed()
        
        embed = discord.Embed(color=Colors.SUCCESS)
        embed.description = f"✅ **{nom}** ajouté ({category.value}) — `{format_price(prix)}`"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove_article", description="Retirer un article du catalogue")
    @app_commands.checks.has_role(ALLOWED_ROLE_ID)
    async def remove_article(self, interaction: discord.Interaction, nom: str):
        async with self.bot.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM ballas_catalog WHERE name = $1", nom)
        
        if result == "DELETE 0":
            return await interaction.response.send_message(f"❌ **{nom}** introuvable.", ephemeral=True)
        
        await self.update_catalog_embed()
        await interaction.response.send_message(f"✅ **{nom}** supprimé.", ephemeral=True)

    @remove_article.autocomplete('nom')
    async def remove_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.article_autocomplete(interaction, current)

    @app_commands.command(name="modif_article", description="Modifier un article (prix et/ou description)")
    @app_commands.checks.has_role(ALLOWED_ROLE_ID)
    async def modif_article(
        self,
        interaction: discord.Interaction,
        nom: str,
        prix: float = None,
        description: str = None
    ):
        if prix is None and description is None:
            return await interaction.response.send_message(
                "❌ Spécifie au moins un paramètre à modifier.", ephemeral=True
            )
        
        async with self.bot.pool.acquire() as conn:
            article = await conn.fetchrow("SELECT * FROM ballas_catalog WHERE name = $1", nom)
            if not article:
                return await interaction.response.send_message(f"❌ **{nom}** introuvable.", ephemeral=True)
            
            new_price = prix if prix is not None else float(article['price'])
            new_desc = description if description is not None else article['description']
            
            await conn.execute(
                "UPDATE ballas_catalog SET price = $1, description = $2 WHERE name = $3",
                new_price, new_desc, nom
            )
        
        await self.update_catalog_embed()
        await interaction.response.send_message(f"✅ **{nom}** mis à jour.", ephemeral=True)

    @modif_article.autocomplete('nom')
    async def modif_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.article_autocomplete(interaction, current)

    @commands.command(name="info_article")
    async def info_article(self, ctx, *, nom: str = None):
        """Voir les détails d'un article"""
        if not nom:
            return await ctx.send("❌ Usage: `!info_article <nom>`")
        
        async with self.bot.pool.acquire() as conn:
            article = await conn.fetchrow("SELECT * FROM ballas_catalog WHERE name ILIKE $1", nom)
        
        if not article:
            return await ctx.send(f"❌ **{nom}** introuvable.")
        
        config = CATEGORY_CONFIG.get(article['category'], {"emoji": "📦"})
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name=article['name'], icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        
        desc = f"**Prix :** {format_price(float(article['price']))}\n**Catégorie :** {config['emoji']} {article['category']}"
        if article['description']:
            desc += f"\n\n_{article['description']}_"
        embed.description = desc
        
        embed.set_footer(text="Ballas — RMB RP")
        
        await ctx.send(embed=embed)

    @commands.command(name="refresh_tarifs")
    @commands.has_permissions(administrator=True)
    async def refresh_tarifs(self, ctx):
        """Rafraîchir l'affichage des tarifs"""
        msg = await ctx.send("⏳ Mise à jour...")
        await self.update_catalog_embed()
        await msg.edit(content="✅ Catalogue mis à jour.")


async def setup(bot):
    await bot.add_cog(TariffCog(bot))
