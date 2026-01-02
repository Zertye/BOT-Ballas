import discord
from discord.ext import commands
from discord import app_commands
import traceback
import sys

sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors, GUILD_ID

# ID autorisé à bypass les permissions admin
OWNER_ID = 393525050206060574

# Fonction de vérification pour les commandes préfixées (!)
def is_owner_or_admin_prefix(ctx):
    return ctx.author.id == OWNER_ID or ctx.author.guild_permissions.administrator

class SetupAllCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        try:
            from cogs.tickets import TicketPanelView, TicketManagementView, CloseConfirmView, PlanningManagementView
            from cogs.absences import AbsencesPanelView
            from cogs.registration import ValidationView, RegisterButtonView
            from cogs.suggestions import SuggestionView
            from cogs.meeting_report import ReportPanelView, ReportValidationView
            from cogs.grade_request import GradeRequestPanelView, GradeValidationView
            
            views = [
                TicketPanelView(), TicketManagementView(), CloseConfirmView(), PlanningManagementView(self.bot),
                AbsencesPanelView(), ValidationView(), RegisterButtonView(), SuggestionView(),
                ReportPanelView(), ReportValidationView(), GradeRequestPanelView(), GradeValidationView()
            ]
            
            for v in views:
                self.bot.add_view(v)
            
            print("✅ [SETUP] Vues persistantes chargées.")
            self.bot.loop.create_task(self.restore())
        except Exception as e:
            print(f"❌ [SETUP] Erreur lors du chargement des vues : {e}")
            traceback.print_exc()

    async def restore(self):
        await self.bot.wait_until_ready()
        if not self.bot.pool:
            print("⚠️ [SETUP] Pas de connexion DB pour restore.")
            return
        try:
            from cogs.tickets import update_planning_embed
            from cogs.absences import update_absences_embed
            await update_planning_embed(self.bot)
            await update_absences_embed(self.bot)
            print("✅ [SETUP] Panels restaurés (Planning & Absences).")
        except Exception as e:
            print(f"❌ [SETUP] Erreur restore: {e}")

    async def save_msg(self, key, msg_id, ch_id):
        if self.bot.pool:
            try:
                async with self.bot.pool.acquire() as conn:
                    await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ($1,$2,$3) ON CONFLICT (key) DO UPDATE SET message_id = $2", key, msg_id, ch_id)
            except Exception as e:
                print(f"⚠️ [SETUP] Erreur sauvegarde DB ({key}): {e}")

    async def safe_purge(self, channel, limit=20):
        """Supprime les messages du bot rapidement et proprement."""
        if not channel: return
        try:
            # check=lambda m: m.author == self.bot.user assure qu'on ne supprime que les messages du bot
            deleted = await channel.purge(limit=limit, check=lambda m: m.author == self.bot.user, bulk=True)
            print(f"   🧹 [PURGE] {len(deleted)} messages supprimés dans {channel.name}")
        except Exception as e:
            print(f"   ⚠️ [PURGE] Erreur purge dans {channel.name}: {e}")
            # Fallback manuel si purge échoue (ex: messages trop vieux)
            async for m in channel.history(limit=limit):
                if m.author == self.bot.user:
                    try: await m.delete()
                    except: pass

    @app_commands.command(name="setup_all", description="Configurer tous les panneaux")
    @app_commands.check(lambda i: i.user.id == OWNER_ID or i.user.guild_permissions.administrator)
    async def setup_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        print("\n--- 🚀 DÉBUT SETUP_ALL ---")
        ok, err = [], []
        
        # === 1. Tickets ===
        print("🔹 [1/8] Configuration Tickets...")
        try:
            cid = CHANNELS.get("tickets_panel")
            if isinstance(cid, int):
                ch = interaction.guild.get_channel(cid)
                if ch:
                    from cogs.tickets import TicketPanelView
                    await self.safe_purge(ch)
                    
                    embed = discord.Embed(color=EMBED_COLOR, description="Sélectionne une catégorie pour ouvrir un ticket.\n\n📅 **Rendez-vous** · Prendre un RDV\n💰 **Achat** · Acheter un produit\n💬 **Autre** · Autre demande")
                    embed.set_author(name="💜 Services Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                    if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                    embed.set_footer(text="Ballas — RMB RP")
                    
                    msg = await ch.send(embed=embed, view=TicketPanelView())
                    await self.save_msg("tickets_panel", msg.id, ch.id)
                    ok.append("Tickets")
                    print("   ✅ Tickets OK")
                else:
                    print(f"   ❌ Salon Tickets introuvable (ID: {cid})")
                    err.append(f"Tickets (Salon {cid} introuvable)")
            else:
                print(f"   ⚠️ Config Tickets invalide: {cid}")
                err.append("Tickets (ID invalide)")
        except Exception as e:
            print(f"   ❌ Erreur Tickets: {e}")
            traceback.print_exc()
            err.append(f"Tickets: {e}")
        
        # === 2. Registration ===
        print("🔹 [2/8] Configuration Enregistrement...")
        try:
            cid = CHANNELS.get("registration")
            if isinstance(cid, int):
                ch = interaction.guild.get_channel(cid)
                if ch:
                    from cogs.registration import RegisterButtonView
                    await self.safe_purge(ch)
                    
                    embed = discord.Embed(color=EMBED_COLOR, description="Clique ci-dessous pour t'enregistrer.")
                    embed.set_author(name="📋 Enregistrement", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                    if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                    embed.set_footer(text="Ballas — RMB RP")
                    
                    msg = await ch.send(embed=embed, view=RegisterButtonView())
                    await self.save_msg("registration", msg.id, ch.id)
                    ok.append("Enregistrement")
                    print("   ✅ Enregistrement OK")
                else:
                    err.append("Enregistrement (Salon introuvable)")
            else:
                err.append("Enregistrement (ID invalide)")
        except Exception as e:
            print(f"   ❌ Erreur Enregistrement: {e}")
            err.append(f"Enregistrement: {e}")
        
        # === 3. Suggestions ===
        print("🔹 [3/8] Configuration Suggestions...")
        try:
            cid = CHANNELS.get("suggestions")
            if isinstance(cid, int):
                ch = interaction.guild.get_channel(cid)
                if ch:
                    from cogs.suggestions import SuggestionView
                    await self.safe_purge(ch)
                    
                    embed = discord.Embed(color=EMBED_COLOR, description="Une idée pour améliorer le gang ?\nPartage-la ici !")
                    embed.set_author(name="💡 Boîte à idées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
                    if BANNER_URL and BANNER_URL != "a config": embed.set_thumbnail(url=BANNER_URL)
                    embed.set_footer(text="Ballas — RMB RP")
                    
                    msg = await ch.send(embed=embed, view=SuggestionView())
                    await self.save_msg("suggestions", msg.id, ch.id)
                    ok.append("Suggestions")
                    print("   ✅ Suggestions OK")
                else:
                    err.append("Suggestions (Salon introuvable)")
            else:
                err.append("Suggestions (ID invalide)")
        except Exception as e:
            print(f"   ❌ Erreur Suggestions: {e}")
            err.append(f"Suggestions: {e}")
        
        # === 4. Absences ===
        print("🔹 [4/8] Configuration Absences...")
        try:
            from cogs.absences import recreate_absences_panel
            await recreate_absences_panel(self.bot)
            ok.append("Absences")
            print("   ✅ Absences OK")
        except Exception as e:
            print(f"   ❌ Erreur Absences: {e}")
            traceback.print_exc()
            err.append(f"Absences: {e}")
        
        # === 5. Planning RDV ===
        print("🔹 [5/8] Configuration Planning...")
        try:
            from cogs.tickets import recreate_planning_panel
            await recreate_planning_panel(self.bot)
            ok.append("Planning RDV")
            print("   ✅ Planning OK")
        except Exception as e:
            print(f"   ❌ Erreur Planning: {e}")
            err.append(f"Planning RDV: {e}")
        
        # === 6. Tarifs ===
        print("🔹 [6/8] Configuration Tarifs...")
        try:
            cog = self.bot.get_cog("TariffCog")
            if cog:
                if self.bot.pool:
                    await cog.update_catalog_embed()
                    ok.append("Tarifs")
                    print("   ✅ Tarifs OK")
                else:
                    print("   ⚠️ Pas de DB pour Tarifs")
                    err.append("Tarifs (DB non connectée)")
            else:
                print("   ⚠️ Cog TariffCog non chargé")
                err.append("Tarifs (Cog non chargé)")
        except Exception as e:
            print(f"   ❌ Erreur Tarifs: {e}")
            err.append(f"Tarifs: {e}")
        
        # === 7. Compte Rendu ===
        print("🔹 [7/8] Configuration Compte Rendu...")
        try:
            from cogs.meeting_report import recreate_report_panel
            await recreate_report_panel(self.bot)
            ok.append("Compte Rendu")
            print("   ✅ Compte Rendu OK")
        except Exception as e:
            print(f"   ❌ Erreur Compte Rendu: {e}")
            err.append(f"Compte Rendu: {e}")
        
        # === 8. Grade Request ===
        print("🔹 [8/8] Configuration Demande de Grade...")
        try:
            from cogs.grade_request import recreate_grade_panel
            await recreate_grade_panel(self.bot)
            ok.append("Demande de Grade")
            print("   ✅ Demande de Grade OK")
        except Exception as e:
            print(f"   ❌ Erreur Demande de Grade: {e}")
            err.append(f"Demande de Grade: {e}")
        
        print(f"--- 🏁 FIN SETUP_ALL (OK: {len(ok)}, ERR: {len(err)}) ---\n")
        
        # Résumé final
        embed = discord.Embed(color=Colors.SUCCESS if not err else Colors.WARNING)
        embed.set_author(name="✅ Configuration terminée" if not err else "⚠️ Configuration partielle", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        if ok: embed.add_field(name="Installés", value="\n".join(f"• {x}" for x in ok), inline=False)
        if err: embed.add_field(name="Erreurs", value="\n".join(f"• {x}" for x in err), inline=False)
        embed.set_footer(text="Regarde la console pour les détails des erreurs.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Afficher toutes les commandes du bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📚 Commandes du Bot Ballas", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        
        slash_cmds = """
`/setup_all` — Configurer tous les panneaux
`/add_article` — Ajouter un article au catalogue
`/remove_article` — Retirer un article du catalogue
`/modif_article` — Modifier un article
`/help` — Afficher cette aide
"""
        embed.add_field(name="⚡ Commandes Slash", value=slash_cmds, inline=False)
        
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
    @commands.check(is_owner_or_admin_prefix)
    async def sync_commands(self, ctx):
        """Resynchroniser les commandes"""
        msg = await ctx.send("⏳ Synchronisation...")
        try:
            guild = discord.Object(id=GUILD_ID)
            self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            embed = discord.Embed(color=Colors.SUCCESS, description=f"**{len(synced)}** commandes actives")
            embed.set_author(name="✅ Commandes synchronisées", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            await msg.edit(content=None, embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Erreur: {e}")

    @commands.command(name="status")
    @commands.check(is_owner_or_admin_prefix)
    async def status(self, ctx):
        """Statut du bot"""
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📊 Statut", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.add_field(name="BDD", value="✅ Connectée" if self.bot.pool else "❌ Déconnectée", inline=True)
        
        ch_status = "\n".join([f"{'✅' if isinstance(v, int) and ctx.guild.get_channel(v) else '❌'} {k}" for k, v in CHANNELS.items()][:10])
        embed.add_field(name="Salons", value=ch_status, inline=False)
        
        if self.bot.pool:
            try:
                async with self.bot.pool.acquire() as conn:
                    abs_count = await conn.fetchval("SELECT COUNT(*) FROM staff_absences")
                    art_count = await conn.fetchval("SELECT COUNT(*) FROM ballas_catalog")
                    reports = await conn.fetchval("SELECT COUNT(*) FROM meeting_reports") or 0
                    grades = await conn.fetchval("SELECT COUNT(*) FROM grade_requests WHERE status = 'pending'") or 0
                embed.add_field(name="Stats", value=f"{abs_count} absences · {art_count} articles · {reports} CR en attente · {grades} demandes de grade", inline=False)
            except Exception as e:
                embed.add_field(name="Erreur DB", value=str(e), inline=False)
        
        embed.set_footer(text="Ballas — RMB RP")
        await ctx.send(embed=embed)

    @commands.command(name="reset_panels")
    @commands.check(is_owner_or_admin_prefix)
    async def reset(self, ctx):
        embed = discord.Embed(color=Colors.WARNING, description="Cela va supprimer et recréer tous les panneaux.\nRéagis avec ✅ pour confirmer.")
        embed.set_author(name="⚠️ Confirmation", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == msg.id
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await msg.edit(embed=discord.Embed(color=EMBED_COLOR, description="⏳ Réinitialisation en cours..."))
            # On utilise le même code que setup_all mais adapté
            await ctx.invoke(self.bot.get_command("setup_tickets"))
            await ctx.invoke(self.bot.get_command("setup_registration"))
            await ctx.invoke(self.bot.get_command("setup_suggestions"))
            await ctx.invoke(self.bot.get_command("setup_absences"))
            await ctx.invoke(self.bot.get_command("setup_report"))
            await ctx.invoke(self.bot.get_command("setup_grade"))
            await ctx.send("✅ Reset terminé (vérifie les salons).")
        except Exception as e:
            await msg.edit(embed=discord.Embed(color=Colors.MUTED, description=f"Annulé ou Erreur: {e}"))

async def setup(bot):
    await bot.add_cog(SetupAllCog(bot))
