import discord
from discord.ext import commands
from discord import app_commands

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors, GUILD_ID


class SetupAllCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        from cogs.tickets import TicketPanelView, TicketManagementView, CloseConfirmView
        from cogs.absences import AbsencesPanelView
        from cogs.registration import ValidationView, RegisterButtonView
        from cogs.suggestions import SuggestionView
        from cogs.meeting_report import ReportPanelView, ReportValidationView
        from cogs.grade_request import GradeRequestPanelView, GradeValidationView
        
        for v in [TicketPanelView(), TicketManagementView(), CloseConfirmView(), AbsencesPanelView(), ValidationView(), RegisterButtonView(), SuggestionView(), ReportPanelView(), ReportValidationView(), GradeRequestPanelView(), GradeValidationView()]:
            self.bot.add_view(v)
        
        print("✅ Vues persistantes chargées.")
        self.bot.loop.create_task(self.restore())

    async def restore(self):
        await self.bot.wait_until_ready()
        if not self.bot.pool:
            return
        try:
            from cogs.absences import update_absences_embed
            await update_absences_embed(self.bot)
        except Exception as e:
            print(f"Erreur restore: {e}")

    async def save_msg(self, key, msg_id, ch_id):
        if self.bot.pool:
            async with self.bot.pool.acquire() as conn:
                await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ($1,$2,$3) ON CONFLICT (key) DO UPDATE SET message_id = $2", key, msg_id, ch_id)

    @app_commands.command(name="setup_all", description="Configurer tous les panneaux")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ok, err = [], []
        
        # Tickets
        try:
            ch = interaction.guild.get_channel(CHANNELS.get("tickets_panel"))
            if ch:
                from cogs.tickets import TicketPanelView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Sélectionne une catégorie pour ouvrir un ticket.\n\n📅 **Rendez-vous** · Prendre un RDV\n💰 **Achat** · Acheter un produit\n💬 **Autre** · Autre demande")
                embed.set_author(name="💜 Services Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=TicketPanelView())
                await self.save_msg("tickets_panel", msg.id, ch.id)
                ok.append("Tickets")
        except Exception as e: err.append(f"Tickets: {e}")
        
        # Registration
        try:
            ch = interaction.guild.get_channel(CHANNELS.get("registration"))
            if ch:
                from cogs.registration import RegisterButtonView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Clique ci-dessous pour t'enregistrer.")
                embed.set_author(name="📋 Enregistrement", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=RegisterButtonView())
                await self.save_msg("registration", msg.id, ch.id)
                ok.append("Enregistrement")
        except Exception as e: err.append(f"Enregistrement: {e}")
        
        # Suggestions
        try:
            ch = interaction.guild.get_channel(CHANNELS.get("suggestions"))
            if ch:
                from cogs.suggestions import SuggestionView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Une idée pour améliorer le gang ?\nPartage-la ici !")
                embed.set_author(name="💡 Boîte à idées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=SuggestionView())
                await self.save_msg("suggestions", msg.id, ch.id)
                ok.append("Suggestions")
        except Exception as e: err.append(f"Suggestions: {e}")
        
        # Absences
        try:
            from cogs.absences import recreate_absences_panel
            await recreate_absences_panel(self.bot)
            ok.append("Absences")
        except Exception as e: err.append(f"Absences: {e}")
        
        # Tarifs
        try:
            cog = self.bot.get_cog("TariffCog")
            if cog and self.bot.pool:
                await cog.update_catalog_embed()
                ok.append("Tarifs")
        except Exception as e: err.append(f"Tarifs: {e}")
        
        # Compte Rendu
        try:
            from cogs.meeting_report import recreate_report_panel
            await recreate_report_panel(self.bot)
            ok.append("Compte Rendu")
        except Exception as e: err.append(f"Compte Rendu: {e}")
        
        # Demande de Grade
        try:
            from cogs.grade_request import recreate_grade_panel
            await recreate_grade_panel(self.bot)
            ok.append("Demande de Grade")
        except Exception as e: err.append(f"Demande de Grade: {e}")
        
        embed = discord.Embed(color=Colors.SUCCESS if not err else Colors.WARNING)
        embed.set_author(name="✅ Configuration terminée" if not err else "⚠️ Configuration partielle", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        if ok: embed.add_field(name="Installés", value="\n".join(f"• {x}" for x in ok), inline=False)
        if err: embed.add_field(name="Erreurs", value="\n".join(f"• {x}" for x in err), inline=False)
        embed.set_footer(text="Ballas — RMB RP")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Afficher toutes les commandes du bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📚 Commandes du Bot Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        
        # Commandes Slash
        slash_cmds = """
`/setup_all` — Configurer tous les panneaux
`/add_article` — Ajouter un article au catalogue
`/remove_article` — Retirer un article du catalogue
`/modif_article` — Modifier un article
`/help` — Afficher cette aide
"""
        embed.add_field(name="⚡ Commandes Slash", value=slash_cmds, inline=False)
        
        # Commandes Admin
        admin_cmds = """
`!sync` — Resynchroniser les commandes
`!status` — Voir le statut du bot
`!reset_panels` — Réinitialiser tous les panneaux
`!setup_tickets` — Installer le panneau tickets
`!setup_absences` — Installer le panneau absences
`!setup_registration` — Installer le panneau enregistrement
`!setup_suggestions` — Installer le panneau suggestions
`!setup_report` — Installer le panneau compte rendu
`!setup_grade` — Installer le panneau demande de grade
"""
        embed.add_field(name="🔧 Administration", value=admin_cmds, inline=False)
        
        # Commandes Gestion
        gestion_cmds = """
`!clear_absences` — Supprimer toutes les absences
`!clear_grades` — Supprimer les demandes de grade en attente
`!test_rapport` — Tester le rapport hebdomadaire
`!refresh_tarifs` — Rafraîchir l'affichage des tarifs
`!info_article <nom>` — Voir les détails d'un article
`!welcome [@membre]` — Tester le message de bienvenue
"""
        embed.add_field(name="📋 Gestion", value=gestion_cmds, inline=False)
        
        embed.set_footer(text="Ballas — RMB RP")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === COMMANDES PRÉFIXÉES ===

    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_commands(self, ctx):
        """Resynchroniser les commandes"""
        msg = await ctx.send("⏳ Synchronisation...")
        
        try:
            guild = discord.Object(id=GUILD_ID)
            self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            
            embed = discord.Embed(color=Colors.SUCCESS)
            embed.set_author(name="✅ Commandes synchronisées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            embed.description = f"**{len(synced)}** commandes actives"
            embed.set_footer(text="Ballas — RMB RP")
            await msg.edit(content=None, embed=embed)
            
        except Exception as e:
            await msg.edit(content=f"❌ Erreur: {e}")

    @commands.command(name="status")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        """Statut du bot"""
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📊 Statut", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="BDD", value="✅ Connectée" if self.bot.pool else "❌ Déconnectée", inline=True)
        
        ch_status = "\n".join([f"{'✅' if ctx.guild.get_channel(v) if isinstance(v, int) else False else '❌'} {k}" for k, v in CHANNELS.items()][:10])
        embed.add_field(name="Salons", value=ch_status, inline=False)
        
        if self.bot.pool:
            async with self.bot.pool.acquire() as conn:
                abs_count = await conn.fetchval("SELECT COUNT(*) FROM staff_absences")
                art_count = await conn.fetchval("SELECT COUNT(*) FROM ballas_catalog")
                reports = await conn.fetchval("SELECT COUNT(*) FROM meeting_reports") or 0
                grades = await conn.fetchval("SELECT COUNT(*) FROM grade_requests WHERE status = 'pending'") or 0
            embed.add_field(name="Stats", value=f"{abs_count} absences · {art_count} articles · {reports} CR en attente · {grades} demandes de grade", inline=False)
        
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.send(embed=embed)

    @commands.command(name="reset_panels")
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx):
        """Réinitialiser les panneaux"""
        embed = discord.Embed(color=Colors.WARNING, description="Cela va supprimer et recréer tous les panneaux.\nRéagis avec ✅ pour confirmer.")
        embed.set_author(name="⚠️ Confirmation", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            if str(reaction.emoji) == "✅":
                await msg.edit(embed=discord.Embed(color=EMBED_COLOR, description="⏳ Réinitialisation en cours..."))
                await self._do_setup_all(ctx)
            else:
                await msg.edit(embed=discord.Embed(color=Colors.MUTED, description="Annulé."))
        except:
            await msg.edit(embed=discord.Embed(color=Colors.MUTED, description="Temps écoulé."))

    async def _do_setup_all(self, ctx):
        """Version interne de setup_all pour les commandes préfixées"""
        ok, err = [], []
        
        # Tickets
        try:
            ch = ctx.guild.get_channel(CHANNELS.get("tickets_panel"))
            if ch:
                from cogs.tickets import TicketPanelView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Sélectionne une catégorie pour ouvrir un ticket.\n\n📅 **Rendez-vous** · Prendre un RDV\n💰 **Achat** · Acheter un produit\n💬 **Autre** · Autre demande")
                embed.set_author(name="💜 Services Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=TicketPanelView())
                await self.save_msg("tickets_panel", msg.id, ch.id)
                ok.append("Tickets")
        except Exception as e: err.append(f"Tickets: {e}")
        
        # Registration
        try:
            ch = ctx.guild.get_channel(CHANNELS.get("registration"))
            if ch:
                from cogs.registration import RegisterButtonView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Clique ci-dessous pour t'enregistrer.")
                embed.set_author(name="📋 Enregistrement", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=RegisterButtonView())
                await self.save_msg("registration", msg.id, ch.id)
                ok.append("Enregistrement")
        except Exception as e: err.append(f"Enregistrement: {e}")
        
        # Suggestions
        try:
            ch = ctx.guild.get_channel(CHANNELS.get("suggestions"))
            if ch:
                from cogs.suggestions import SuggestionView
                async for m in ch.history(limit=20):
                    if m.author == self.bot.user: await m.delete()
                embed = discord.Embed(color=EMBED_COLOR, description="Une idée pour améliorer le gang ?\nPartage-la ici !")
                embed.set_author(name="💡 Boîte à idées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                embed.set_footer(text="Ballas — RMB RP")
                msg = await ch.send(embed=embed, view=SuggestionView())
                await self.save_msg("suggestions", msg.id, ch.id)
                ok.append("Suggestions")
        except Exception as e: err.append(f"Suggestions: {e}")
        
        # Absences
        try:
            from cogs.absences import recreate_absences_panel
            await recreate_absences_panel(self.bot)
            ok.append("Absences")
        except Exception as e: err.append(f"Absences: {e}")
        
        # Tarifs
        try:
            cog = self.bot.get_cog("TariffCog")
            if cog and self.bot.pool:
                await cog.update_catalog_embed()
                ok.append("Tarifs")
        except Exception as e: err.append(f"Tarifs: {e}")
        
        # Compte Rendu
        try:
            from cogs.meeting_report import recreate_report_panel
            await recreate_report_panel(self.bot)
            ok.append("Compte Rendu")
        except Exception as e: err.append(f"Compte Rendu: {e}")
        
        # Demande de Grade
        try:
            from cogs.grade_request import recreate_grade_panel
            await recreate_grade_panel(self.bot)
            ok.append("Demande de Grade")
        except Exception as e: err.append(f"Demande de Grade: {e}")
        
        embed = discord.Embed(color=Colors.SUCCESS if not err else Colors.WARNING)
        embed.set_author(name="✅ Configuration terminée" if not err else "⚠️ Configuration partielle", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        if ok: embed.add_field(name="Installés", value="\n".join(f"• {x}" for x in ok), inline=False)
        if err: embed.add_field(name="Erreurs", value="\n".join(f"• {x}" for x in err), inline=False)
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SetupAllCog(bot))
