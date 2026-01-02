import discord
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from zoneinfo import ZoneInfo

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, CHANNELS, ROLES, Colors

# Fuseau horaire français
PARIS_TZ = ZoneInfo("Europe/Paris")

# Heure du rapport : Dimanche 12h00
REPORT_TIME = datetime.time(hour=12, minute=0, tzinfo=PARIS_TZ)


def parse_date(s: str):
    for fmt in ["%d/%m/%Y", "%d/%m"]:
        try:
            dt = datetime.datetime.strptime(s.strip(), fmt)
            if fmt == "%d/%m":
                now = datetime.datetime.now()
                dt = dt.replace(year=now.year if dt.replace(year=now.year).date() >= now.date() else now.year + 1)
            return dt.date()
        except: pass
    return None


def format_date(dt):
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{dt.day} {months[dt.month-1]}"


def format_date_full(dt):
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{days[dt.weekday()]} {dt.day} {months[dt.month-1]}"


def get_week_bounds():
    """Retourne le lundi et dimanche de la semaine en cours"""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


async def update_absences_embed(bot):
    if not bot.pool:
        return
    channel = bot.get_channel(CHANNELS.get("absences"))
    if not channel:
        return
    
    today = datetime.date.today()
    async with bot.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM staff_absences WHERE end_date >= $1 ORDER BY start_date LIMIT 20", today.isoformat())
        cfg = await conn.fetchrow("SELECT message_id FROM persistent_messages WHERE key = 'absences_panel'")
        msg_id = cfg["message_id"] if cfg else None
    
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name="📋 Absences des membres", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    
    if not rows:
        embed.description = "*Aucune absence déclarée*"
    else:
        en_cours = [r for r in rows if datetime.date.fromisoformat(r['start_date']) <= today <= datetime.date.fromisoformat(r['end_date'])]
        a_venir = [r for r in rows if datetime.date.fromisoformat(r['start_date']) > today]
        
        lines = []
        if en_cours:
            lines.append("**🔴 En cours**")
            for r in en_cours:
                u = bot.get_user(r['staff_id'])
                start, end = datetime.date.fromisoformat(r['start_date']), datetime.date.fromisoformat(r['end_date'])
                left = (end - today).days
                lines.append(f"**{u.display_name if u else 'Inconnu'}** · {format_date(start)} → {format_date(end)} ({left}j)" + (f"\n_{r['reason']}_" if r['reason'] else ""))
            lines.append("")
        if a_venir:
            lines.append("**🟡 À venir**")
            for r in a_venir:
                u = bot.get_user(r['staff_id'])
                start, end = datetime.date.fromisoformat(r['start_date']), datetime.date.fromisoformat(r['end_date'])
                until = (start - today).days
                lines.append(f"**{u.display_name if u else 'Inconnu'}** · dans {until}j\n{format_date(start)} → {format_date(end)}" + (f"\n_{r['reason']}_" if r['reason'] else ""))
        embed.description = "\n".join(lines)
    
    total = len([r for r in rows if datetime.date.fromisoformat(r['start_date']) <= today <= datetime.date.fromisoformat(r['end_date'])])
    embed.set_footer(text=f"{total} absent(s) · Ballas — RMB RP")
    
    try:
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=AbsencesPanelView())
                return
            except discord.NotFound:
                pass
        msg = await channel.send(embed=embed, view=AbsencesPanelView())
        async with bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ('absences_panel', $1, $2) ON CONFLICT (key) DO UPDATE SET message_id = $1", msg.id, channel.id)
    except Exception as e:
        print(f"[ABSENCES] Erreur: {e}")


async def recreate_absences_panel(bot):
    """Supprime et recrée le panneau des absences (utilisé par setup_all)"""
    if not bot.pool:
        return
    channel = bot.get_channel(CHANNELS.get("absences"))
    if not channel:
        return
    
    # Supprimer l'ancien message
    async with bot.pool.acquire() as conn:
        cfg = await conn.fetchrow("SELECT message_id FROM persistent_messages WHERE key = 'absences_panel'")
        if cfg:
            try:
                old_msg = await channel.fetch_message(cfg["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass
            await conn.execute("DELETE FROM persistent_messages WHERE key = 'absences_panel'")
    
    # Créer le nouveau
    today = datetime.date.today()
    async with bot.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM staff_absences WHERE end_date >= $1 ORDER BY start_date LIMIT 20", today.isoformat())
    
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name="📋 Absences des membres", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    
    if not rows:
        embed.description = "*Aucune absence déclarée*"
    else:
        en_cours = [r for r in rows if datetime.date.fromisoformat(r['start_date']) <= today <= datetime.date.fromisoformat(r['end_date'])]
        a_venir = [r for r in rows if datetime.date.fromisoformat(r['start_date']) > today]
        
        lines = []
        if en_cours:
            lines.append("**🔴 En cours**")
            for r in en_cours:
                u = bot.get_user(r['staff_id'])
                start, end = datetime.date.fromisoformat(r['start_date']), datetime.date.fromisoformat(r['end_date'])
                left = (end - today).days
                lines.append(f"**{u.display_name if u else 'Inconnu'}** · {format_date(start)} → {format_date(end)} ({left}j)" + (f"\n_{r['reason']}_" if r['reason'] else ""))
            lines.append("")
        if a_venir:
            lines.append("**🟡 À venir**")
            for r in a_venir:
                u = bot.get_user(r['staff_id'])
                start, end = datetime.date.fromisoformat(r['start_date']), datetime.date.fromisoformat(r['end_date'])
                until = (start - today).days
                lines.append(f"**{u.display_name if u else 'Inconnu'}** · dans {until}j\n{format_date(start)} → {format_date(end)}" + (f"\n_{r['reason']}_" if r['reason'] else ""))
        embed.description = "\n".join(lines)
    
    total = len([r for r in rows if datetime.date.fromisoformat(r['start_date']) <= today <= datetime.date.fromisoformat(r['end_date'])]) if rows else 0
    embed.set_footer(text=f"{total} absent(s) · Ballas — RMB RP")
    
    msg = await channel.send(embed=embed, view=AbsencesPanelView())
    async with bot.pool.acquire() as conn:
        await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ('absences_panel', $1, $2) ON CONFLICT (key) DO UPDATE SET message_id = $1", msg.id, channel.id)


class AbsencesPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Déclarer une absence", style=discord.ButtonStyle.primary, emoji="📝", custom_id="absence_declare_ballas")
    async def declare(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(ROLES["support"]) not in interaction.user.roles:
            return await interaction.response.send_message("❌ Réservé aux membres du gang.", ephemeral=True)
        await interaction.response.send_modal(AbsenceModal())

    @discord.ui.button(label="Annuler mon absence", style=discord.ButtonStyle.danger, emoji="❌", custom_id="absence_cancel_ballas")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        bot = interaction.client
        if not bot.pool:
            return await interaction.response.send_message("❌ Base de données indisponible.", ephemeral=True)
        
        async with bot.pool.acquire() as conn:
            absences = await conn.fetch(
                "SELECT * FROM staff_absences WHERE staff_id = $1 AND end_date >= $2 ORDER BY start_date",
                interaction.user.id,
                datetime.date.today().isoformat()
            )
        
        if not absences:
            return await interaction.response.send_message("📭 Tu n'as aucune absence déclarée.", ephemeral=True)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="🗑️ Annuler une absence", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = "Sélectionne l'absence à annuler :"
        
        await interaction.response.send_message(
            embed=embed,
            view=CancelAbsenceView(bot, interaction.user.id, absences),
            ephemeral=True
        )


class CancelAbsenceView(discord.ui.View):
    def __init__(self, bot, user_id, absences):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        
        options = []
        for a in absences:
            start = datetime.date.fromisoformat(a['start_date'])
            end = datetime.date.fromisoformat(a['end_date'])
            label = f"{format_date(start)} → {format_date(end)}"
            desc = (a['reason'] or "Pas de raison")[:50]
            options.append(discord.SelectOption(label=label, description=desc, value=str(a['id'])))
        
        select = discord.ui.Select(
            placeholder="Choisir l'absence à annuler",
            options=options,
            custom_id="absence_cancel_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        absence_id = int(interaction.data["values"][0])
        
        async with self.bot.pool.acquire() as conn:
            absence = await conn.fetchrow(
                "SELECT * FROM staff_absences WHERE id = $1 AND staff_id = $2",
                absence_id,
                self.user_id
            )
            
            if not absence:
                return await interaction.response.edit_message(
                    content="❌ Cette absence n'existe pas ou ne t'appartient pas.",
                    embed=None,
                    view=None
                )
            
            await conn.execute("DELETE FROM staff_absences WHERE id = $1", absence_id)
        
        await update_absences_embed(self.bot)
        
        start = datetime.date.fromisoformat(absence['start_date'])
        end = datetime.date.fromisoformat(absence['end_date'])
        
        embed = discord.Embed(color=Colors.SUCCESS)
        embed.set_author(name="✅ Absence annulée", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"**{format_date(start)} → {format_date(end)}**\n_{absence['reason'] or 'Pas de raison'}_"
        
        await interaction.response.edit_message(embed=embed, view=None)


class AbsenceModal(discord.ui.Modal, title="Déclarer une absence"):
    start = discord.ui.TextInput(label="Début", placeholder="25/12 ou 25/12/2024", max_length=10)
    end = discord.ui.TextInput(label="Fin", placeholder="02/01 ou 02/01/2025", max_length=10)
    reason = discord.ui.TextInput(label="Raison (optionnel)", style=discord.TextStyle.long, required=False, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        s, e = parse_date(self.start.value), parse_date(self.end.value)
        
        if not s:
            return await interaction.followup.send("❌ Date de début invalide.", ephemeral=True)
        if not e:
            return await interaction.followup.send("❌ Date de fin invalide.", ephemeral=True)
        if e < s:
            return await interaction.followup.send("❌ La fin doit être après le début.", ephemeral=True)
        if e < datetime.date.today():
            return await interaction.followup.send("❌ Période déjà passée.", ephemeral=True)
        
        bot = interaction.client
        if bot.pool:
            async with bot.pool.acquire() as conn:
                if await conn.fetchval("SELECT COUNT(*) FROM staff_absences WHERE staff_id = $1 AND NOT (end_date < $2 OR start_date > $3)", interaction.user.id, s.isoformat(), e.isoformat()) > 0:
                    return await interaction.followup.send("❌ Tu as déjà une absence sur cette période.", ephemeral=True)
                await conn.execute("INSERT INTO staff_absences (staff_id, start_date, end_date, reason) VALUES ($1, $2, $3, $4)", interaction.user.id, s.isoformat(), e.isoformat(), self.reason.value or None)
        
        await update_absences_embed(bot)
        
        embed = discord.Embed(color=Colors.SUCCESS, description=f"**{format_date(s)} → {format_date(e)}**\n_{self.reason.value or 'Pas de raison'}_")
        embed.set_author(name="✅ Absence enregistrée", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        await interaction.followup.send(embed=embed, ephemeral=True)


class AbsencesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Démarrer les tâches au chargement du cog"""
        self.check_absences.start()
        self.weekly_report.start()

    async def cog_unload(self):
        """Arrêter les tâches lors du déchargement du cog"""
        self.check_absences.cancel()
        self.weekly_report.cancel()

    @tasks.loop(hours=24)
    async def check_absences(self):
        """Vérifie et nettoie les absences toutes les 24h"""
        if not self.bot.pool:
            return
        
        today = datetime.date.today()
        cleanup_date = (today - datetime.timedelta(days=8)).isoformat()
        
        async with self.bot.pool.acquire() as conn:
            deleted = await conn.execute(
                "DELETE FROM staff_absences WHERE end_date < $1",
                cleanup_date
            )
            
            if deleted and deleted != "DELETE 0":
                count = int(deleted.split(" ")[1])
                print(f"[ABSENCES] {count} absence(s) archivée(s) supprimée(s)")
        
        await update_absences_embed(self.bot)
        print(f"[ABSENCES] Vérification quotidienne effectuée - {today}")

    @check_absences.before_loop
    async def before_check_absences(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=REPORT_TIME)
    async def weekly_report(self):
        """Envoie le rapport hebdomadaire tous les dimanches à 12h00"""
        now = datetime.datetime.now(PARIS_TZ)
        if now.weekday() != 6:
            return
        
        if not self.bot.pool:
            return
        
        channel = self.bot.get_channel(CHANNELS.get("absences"))
        if not channel:
            print("[ABSENCES] Salon introuvable pour le rapport")
            return
        
        await self.send_weekly_report(channel)

    @weekly_report.before_loop
    async def before_weekly_report(self):
        await self.bot.wait_until_ready()

    async def send_weekly_report(self, channel: discord.TextChannel):
        """Génère et envoie le rapport hebdomadaire"""
        today = datetime.date.today()
        monday, sunday = get_week_bounds()
        
        async with self.bot.pool.acquire() as conn:
            all_absences = await conn.fetch("SELECT * FROM staff_absences ORDER BY start_date")
        
        nouvelles = []
        terminees = []
        en_cours = []
        a_venir = []
        
        for a in all_absences:
            start = datetime.date.fromisoformat(a['start_date'])
            end = datetime.date.fromisoformat(a['end_date'])
            created = a['created_at'].date() if a['created_at'] else start
            
            if created >= monday:
                nouvelles.append(a)
            
            if monday <= end <= sunday and end < today:
                terminees.append(a)
            
            if start <= today <= end:
                en_cours.append(a)
            
            if start > today:
                a_venir.append(a)
        
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="📊 Rapport Hebdomadaire des Absences", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.description = f"**Semaine du {format_date_full(monday)} au {format_date_full(sunday)}**"
        
        if nouvelles:
            lines = []
            for a in nouvelles:
                u = self.bot.get_user(a['staff_id'])
                start = datetime.date.fromisoformat(a['start_date'])
                end = datetime.date.fromisoformat(a['end_date'])
                name = u.display_name if u else f"ID: {a['staff_id']}"
                lines.append(f"• **{name}**\n  {format_date(start)} → {format_date(end)}" + (f"\n  _{a['reason']}_" if a['reason'] else ""))
            embed.add_field(
                name=f"🆕 Nouvelles absences déclarées ({len(nouvelles)})",
                value="\n".join(lines) or "*Aucune*",
                inline=False
            )
        else:
            embed.add_field(
                name="🆕 Nouvelles absences déclarées (0)",
                value="*Aucune nouvelle absence cette semaine*",
                inline=False
            )
        
        if terminees:
            lines = []
            for a in terminees:
                u = self.bot.get_user(a['staff_id'])
                start = datetime.date.fromisoformat(a['start_date'])
                end = datetime.date.fromisoformat(a['end_date'])
                name = u.display_name if u else f"ID: {a['staff_id']}"
                duration = (end - start).days + 1
                lines.append(f"• **{name}** — {duration} jour(s)\n  {format_date(start)} → {format_date(end)}")
            embed.add_field(
                name=f"✅ Absences terminées cette semaine ({len(terminees)})",
                value="\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Absences terminées cette semaine (0)",
                value="*Aucune absence terminée*",
                inline=False
            )
        
        if en_cours:
            lines = []
            for a in en_cours:
                u = self.bot.get_user(a['staff_id'])
                start = datetime.date.fromisoformat(a['start_date'])
                end = datetime.date.fromisoformat(a['end_date'])
                name = u.display_name if u else f"ID: {a['staff_id']}"
                left = (end - today).days
                lines.append(f"• **{name}** — encore {left}j\n  Retour le {format_date_full(end + datetime.timedelta(days=1))}")
            embed.add_field(
                name=f"🔴 Actuellement absents ({len(en_cours)})",
                value="\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(
                name="🔴 Actuellement absents (0)",
                value="*Tout le monde est présent !*",
                inline=False
            )
        
        if a_venir:
            lines = []
            for a in a_venir[:5]:
                u = self.bot.get_user(a['staff_id'])
                start = datetime.date.fromisoformat(a['start_date'])
                end = datetime.date.fromisoformat(a['end_date'])
                name = u.display_name if u else f"ID: {a['staff_id']}"
                until = (start - today).days
                lines.append(f"• **{name}** — dans {until}j\n  {format_date(start)} → {format_date(end)}")
            if len(a_venir) > 5:
                lines.append(f"_... et {len(a_venir) - 5} autre(s)_")
            embed.add_field(
                name=f"🟡 Absences à venir ({len(a_venir)})",
                value="\n".join(lines),
                inline=False
            )
        
        total_jours = sum(
            (datetime.date.fromisoformat(a['end_date']) - datetime.date.fromisoformat(a['start_date'])).days + 1
            for a in nouvelles
        )
        
        stats = f"📈 **{len(nouvelles)}** nouvelle(s) absence(s) · **{total_jours}** jour(s) d'absence déclarés"
        embed.add_field(name="📊 Statistiques", value=stats, inline=False)
        
        embed.set_footer(text=f"Rapport généré le {format_date_full(today)} à 12h00 · Ballas — RMB RP")
        embed.timestamp = datetime.datetime.now(PARIS_TZ)
        
        await channel.send(embed=embed)
        print(f"[ABSENCES] Rapport hebdomadaire envoyé - {today}")

    @commands.command(name="setup_absences")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """Installer le panneau des absences"""
        embed = discord.Embed(color=EMBED_COLOR, description="*Aucune absence déclarée*")
        embed.set_author(name="📋 Absences des membres", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        embed.set_footer(text="0 absent(s) · Ballas — RMB RP")
        msg = await ctx.channel.send(embed=embed, view=AbsencesPanelView())
        if self.bot.pool:
            async with self.bot.pool.acquire() as conn:
                await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ('absences_panel', $1, $2) ON CONFLICT (key) DO UPDATE SET message_id = $1", msg.id, ctx.channel.id)
        await ctx.message.add_reaction("✅")

    @commands.command(name="clear_absences")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx):
        """Supprimer toutes les absences"""
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM staff_absences")
        await update_absences_embed(self.bot)
        await ctx.send(f"✅ {r.split(' ')[1] if r else 0} absences supprimées.")

    @commands.command(name="test_rapport")
    @commands.has_permissions(administrator=True)
    async def test_report(self, ctx):
        """Tester le rapport hebdomadaire"""
        msg = await ctx.send("⏳ Génération du rapport...")
        await self.send_weekly_report(ctx.channel)
        await msg.edit(content="✅ Rapport envoyé.")


async def setup(bot):
    await bot.add_cog(AbsencesCog(bot))
