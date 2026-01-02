import discord
from discord.ext import commands
from discord import app_commands

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors

# Salon où s'affiche le panneau (bouton) pour les membres
PANEL_CHANNEL_ID = CHANNELS.get("grade_requests")

# Salon où arrivent les demandes pour le staff (Centralisé)
VALIDATION_CHANNEL_ID = CHANNELS.get("requests_validation")

MAX_PENDING_REQUESTS = 2


async def get_pending_requests_count(bot, user_id: int) -> int:
    """Compte le nombre de demandes en attente pour un utilisateur"""
    if not bot.pool:
        return 0
    async with bot.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM grade_requests WHERE user_id = $1 AND status = 'pending'",
            user_id
        )
        return count or 0


class GradeRequestPanelView(discord.ui.View):
    """Vue principale du panneau de demande de grade"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Demander un grade", style=discord.ButtonStyle.primary, emoji="📈", custom_id="grade_request_start_ballas")
    async def start_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        bot = interaction.client
        
        pending_count = await get_pending_requests_count(bot, interaction.user.id)
        if pending_count >= MAX_PENDING_REQUESTS:
            return await interaction.response.send_message(
                f"❌ Tu as déjà {pending_count} demande(s) en attente.",
                ephemeral=True
            )
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📈 Demande de Grade", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "Sélectionne le grade que tu souhaites demander."
        embed.set_footer(text=f"Demandes en attente: {pending_count}/{MAX_PENDING_REQUESTS} · Ballas — RMB RP")
        
        await interaction.response.send_message(embed=embed, view=GradeSelectView(), ephemeral=True)


class GradeSelectView(discord.ui.View):
    """Vue pour sélectionner un grade"""
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Choisis un grade", min_values=1, max_values=1, custom_id="grade_select")
    async def select_grade(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        bot = interaction.client
        
        if role in interaction.user.roles:
            return await interaction.response.send_message(f"❌ Tu as déjà le grade {role.mention}.", ephemeral=True)
        
        pending_count = await get_pending_requests_count(bot, interaction.user.id)
        if pending_count >= MAX_PENDING_REQUESTS:
            return await interaction.response.send_message(f"❌ Limite de demandes atteinte.", ephemeral=True)
        
        if bot.pool:
            async with bot.pool.acquire() as conn:
                existing = await conn.fetchval(
                    "SELECT id FROM grade_requests WHERE user_id = $1 AND role_id = $2 AND status = 'pending'",
                    interaction.user.id, role.id
                )
                if existing:
                    return await interaction.response.send_message(f"❌ Demande déjà en cours pour {role.mention}.", ephemeral=True)
        
        # Envoi dans le salon de validation centralisé
        channel = interaction.guild.get_channel(VALIDATION_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("❌ Salon de validation introuvable.", ephemeral=True)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📈 Nouvelle Demande de Grade", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Membre", value=interaction.user.mention, inline=True)
        embed.add_field(name="Grade demandé", value=role.mention, inline=True)
        
        roles_str = ", ".join([r.mention for r in interaction.user.roles if r != interaction.guild.default_role][:5])
        embed.add_field(name="Grades actuels", value=roles_str or "Aucun", inline=False)
        
        embed.set_footer(text=f"ID: {interaction.user.id} | Rôle: {role.id}")
        
        msg = await channel.send(embed=embed, view=GradeValidationView())
        
        if bot.pool:
            async with bot.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO grade_requests (user_id, role_id, message_id, status) VALUES ($1, $2, $3, 'pending')",
                    interaction.user.id, role.id, msg.id
                )
        
        success = discord.Embed(color=Colors.SUCCESS, description=f"Ta demande pour {role.mention} a été envoyée.")
        await interaction.response.edit_message(embed=success, view=None)


class GradeValidationView(discord.ui.View):
    """Vue de validation des demandes de grade (persistante)"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, emoji="✅", custom_id="grade_request_accept_ballas")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(ROLES.get("support"))
        if staff_role and staff_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        
        try:
            parts = interaction.message.embeds[0].footer.text.split(" | ")
            user_id = int(parts[0].replace("ID: ", ""))
            role_id = int(parts[1].replace("Rôle: ", ""))
        except:
            return await interaction.response.send_message("❌ Erreur données.", ephemeral=True)
        
        member = interaction.guild.get_member(user_id)
        role = interaction.guild.get_role(role_id)
        
        bot = interaction.client
        if not member:
            if bot.pool:
                async with bot.pool.acquire() as conn:
                    await conn.execute("UPDATE grade_requests SET status = 'rejected' WHERE message_id = $1", interaction.message.id)
            embed = interaction.message.embeds[0]
            embed.color = Colors.ERROR
            embed.set_author(name="❌ Membre parti", icon_url=LOGO_URL)
            for c in self.children: c.disabled = True
            await interaction.message.edit(embed=embed, view=self)
            return await interaction.response.send_message("❌ Membre parti.", ephemeral=True)
        
        try:
            await member.add_roles(role)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erreur rôle: {e}", ephemeral=True)
        
        if bot.pool:
            async with bot.pool.acquire() as conn:
                await conn.execute("UPDATE grade_requests SET status = 'accepted' WHERE message_id = $1", interaction.message.id)
        
        embed = interaction.message.embeds[0]
        embed.color = Colors.SUCCESS
        embed.set_author(name="✅ Demande de Grade Acceptée", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="Validé par", value=interaction.user.mention, inline=False)
        for c in self.children: c.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✅ Grade donné à {member.mention}.", ephemeral=True)
        
        try:
            dm = discord.Embed(color=Colors.SUCCESS, description=f"Ta demande pour le grade **{role.name}** a été acceptée !")
            dm.set_author(name="✅ Grade obtenu", icon_url=LOGO_URL)
            await member.send(embed=dm)
        except: pass

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, emoji="❌", custom_id="grade_request_refuse_ballas")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(ROLES.get("support"))
        if staff_role and staff_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        
        try:
            parts = interaction.message.embeds[0].footer.text.split(" | ")
            user_id = int(parts[0].replace("ID: ", ""))
            role_id = int(parts[1].replace("Rôle: ", ""))
        except:
            return await interaction.response.send_message("❌ Erreur données.", ephemeral=True)
        
        bot = interaction.client
        if bot.pool:
            async with bot.pool.acquire() as conn:
                await conn.execute("UPDATE grade_requests SET status = 'rejected' WHERE message_id = $1", interaction.message.id)
        
        embed = interaction.message.embeds[0]
        embed.color = Colors.ERROR
        embed.set_author(name="❌ Demande de Grade Refusée", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="Refusé par", value=interaction.user.mention, inline=False)
        for c in self.children: c.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("❌ Demande refusée.", ephemeral=True)
        
        member = interaction.guild.get_member(user_id)
        role = interaction.guild.get_role(role_id)
        if member:
            try:
                description = f"Ta demande pour le grade **{role.name if role else 'inconnu'}** a été refusée.\n\n"
                description += "**Rappel :** pour obtenir le grade citoyen merci de vous enregistrer dans https://discord.com/channels/1137511104487112724/1456661043731501056"
                
                dm = discord.Embed(color=Colors.ERROR, description=description)
                dm.set_author(name="❌ Demande refusée", icon_url=LOGO_URL)
                await member.send(embed=dm)
            except: pass


async def recreate_grade_panel(bot):
    """Supprime et recrée le panneau de demande de grade"""
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if not channel:
        return
    
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            embed = msg.embeds[0]
            # On cherche le panneau principal pour le supprimer/recharger
            if embed.author and "Demande de Grade" in (embed.author.name or "") and "Sélectionne" in (embed.description or ""):
                await msg.delete()
                break
            # Supprimer aussi s'il y a un vieux panneau qui traine
            if embed.author and "Demande de Grade" in (embed.author.name or "") and len(msg.components) > 0 and "Demandes en attente" not in (embed.footer.text or ""):
                 await msg.delete()

    
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name="📈 Demande de Grade", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    embed.description = (
        "Tu veux monter en grade ?\n\n"
        "Clique sur le bouton ci-dessous pour faire ta demande.\n"
        f"**Limite :** {MAX_PENDING_REQUESTS} demandes simultanées maximum."
    )
    if BANNER_URL and BANNER_URL != "a config":
        embed.set_thumbnail(url=BANNER_URL)
    embed.set_footer(text="Ballas — RMB RP")
    
    await channel.send(embed=embed, view=GradeRequestPanelView())


class GradeRequestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if self.bot.pool:
            async with self.bot.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS grade_requests (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        role_id BIGINT NOT NULL,
                        message_id BIGINT UNIQUE,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

    @commands.command(name="setup_grade")
    @commands.has_permissions(administrator=True)
    async def setup_grade(self, ctx):
        await recreate_grade_panel(self.bot)
        await ctx.message.add_reaction("✅")

    @commands.command(name="clear_grades")
    @commands.has_permissions(administrator=True)
    async def clear_grades(self, ctx):
        if not self.bot.pool:
            return await ctx.send("❌ Base de données indisponible.")
        async with self.bot.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM grade_requests WHERE status = 'pending'")
            count = int(result.split(" ")[1]) if result else 0
        await ctx.send(f"✅ {count} demande(s) en attente supprimée(s).")


async def setup(bot):
    await bot.add_cog(GradeRequestCog(bot))
