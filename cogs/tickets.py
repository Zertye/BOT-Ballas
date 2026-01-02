import discord
import io
import datetime
from discord.ext import commands
from discord import app_commands

import sys
sys.path.append("..")
from config import EMBED_COLOR, LOGO_URL, BANNER_URL, CHANNELS, ROLES, Colors, GUILD_ID


def get_next_rdv_timestamp(day_name: str, hour_str: str) -> int:
    days_map = {"Lundi": 0, "Mardi": 1, "Mercredi": 2, "Jeudi": 3, "Vendredi": 4, "Samedi": 5, "Dimanche": 6}
    target_day_idx = days_map.get(day_name)
    if target_day_idx is None:
        return 0
    try:
        hour = int(hour_str.replace('h', '').replace(':', ''))
        if hour > 100:
            hour = hour // 100
    except:
        hour = 18
    now = datetime.datetime.now()
    days_ahead = target_day_idx - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.hour >= hour):
        days_ahead += 7
    next_date = now + datetime.timedelta(days=days_ahead)
    return int(next_date.replace(hour=hour, minute=0, second=0, microsecond=0).timestamp())


def get_day_options() -> list[discord.SelectOption]:
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    options = []
    now = datetime.datetime.now()
    for i, day in enumerate(days):
        ahead = i - now.weekday()
        if ahead <= 0:
            ahead += 7
        date = now + datetime.timedelta(days=ahead)
        options.append(discord.SelectOption(label=f"{day} {date.day} {months[date.month-1]}", value=day))
    return options


def format_date_french(day_name: str, hour_str: str) -> str:
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    ts = get_next_rdv_timestamp(day_name, hour_str)
    dt = datetime.datetime.fromtimestamp(ts)
    return f"{days[dt.weekday()]} {dt.day} {months[dt.month-1]} à {hour_str}"


async def generate_transcript(channel: discord.TextChannel) -> io.StringIO:
    lines = [f"TRANSCRIPT — {channel.name}", f"Date : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", "-" * 50, ""]
    async for msg in channel.history(limit=None, oldest_first=True):
        ts = msg.created_at.strftime('%d/%m %H:%M')
        content = msg.content + (f" [Fichier: {msg.attachments[0].url}]" if msg.attachments else "")
        lines.append(f"[{ts}] {msg.author.name}: {content}")
    return io.StringIO("\n".join(lines))


async def check_slot_available(bot, timestamp: int) -> bool:
    if not bot.pool:
        return True
    async with bot.pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM rdv_planning WHERE ABS(rdv_timestamp - $1) < 1800", timestamp) == 0


async def finalize_rdv(bot, channel, user, staff, day, hour, ts, to_delete=None):
    if to_delete:
        for msg in to_delete:
            try: await msg.delete()
            except: pass
    
    if bot.pool:
        async with bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO rdv_planning (user_id, staff_id, day, hour, rdv_timestamp, channel_id) VALUES ($1, $2, $3, $4, $5, $6)", user.id, staff.id, day, hour, ts, channel.id)
    
    await update_planning_embed(bot)
    
    embed = discord.Embed(color=Colors.SUCCESS)
    embed.set_author(name="✅ RDV confirmé", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    embed.description = f"**{format_date_french(day, hour)}**\n\nClient : {user.mention}\nResponsable : {staff.mention}"
    embed.set_footer(text="Ballas — RMB RP")
    await channel.send(embed=embed)


async def update_planning_embed(bot):
    if not bot.pool:
        return
    channel = bot.get_channel(CHANNELS.get("rdv_planning"))
    if not channel:
        return
    
    now_ts = int(datetime.datetime.now().timestamp())
    days_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    months_fr = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    
    async with bot.pool.acquire() as conn:
        await conn.execute("DELETE FROM rdv_planning WHERE rdv_timestamp < $1", now_ts - 7200)
        rows = await conn.fetch("SELECT * FROM rdv_planning WHERE rdv_timestamp > $1 ORDER BY rdv_timestamp ASC LIMIT 15", now_ts - 3600)
        config = await conn.fetchrow("SELECT message_id FROM persistent_messages WHERE key = 'rdv_planning'")
        msg_id = config["message_id"] if config else None
    
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name="📅 Planning des RDV", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
    
    if not rows:
        embed.description = "*Aucun RDV programmé*"
    else:
        by_day = {}
        for r in rows:
            key = datetime.datetime.fromtimestamp(r['rdv_timestamp']).strftime('%Y-%m-%d')
            by_day.setdefault(key, []).append(r)
        
        lines = []
        for key in sorted(by_day.keys()):
            dt = datetime.datetime.fromtimestamp(by_day[key][0]['rdv_timestamp'])
            lines.append(f"**{days_fr[dt.weekday()]} {dt.day} {months_fr[dt.month-1]}**")
            for r in by_day[key]:
                u = bot.get_user(r['user_id'])
                s = bot.get_user(r['staff_id'])
                h = datetime.datetime.fromtimestamp(r['rdv_timestamp'])
                lines.append(f"`{h.hour:02d}h{h.minute:02d}` {u.display_name if u else 'Inconnu'} → {s.display_name if s else 'Staff'}")
            lines.append("")
        embed.description = "\n".join(lines)
    
    embed.set_footer(text=f"{len(rows)} RDV · Ballas — RMB RP")
    view = PlanningManagementView(bot) if rows else None
    
    try:
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass
        msg = await channel.send(embed=embed, view=view)
        async with bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO persistent_messages (key, message_id, channel_id) VALUES ('rdv_planning', $1, $2) ON CONFLICT (key) DO UPDATE SET message_id = $1", msg.id, channel.id)
    except Exception as e:
        print(f"[PLANNING] Erreur: {e}")


async def recreate_planning_panel(bot):
    """Supprime et recrée le panneau du planning (utilisé par setup_all)"""
    if not bot.pool:
        return
    channel = bot.get_channel(CHANNELS.get("rdv_planning"))
    if not channel:
        return
    
    # Supprimer l'ancien message
    async with bot.pool.acquire() as conn:
        cfg = await conn.fetchrow("SELECT message_id FROM persistent_messages WHERE key = 'rdv_planning'")
        if cfg:
            try:
                old_msg = await channel.fetch_message(cfg["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass
            await conn.execute("DELETE FROM persistent_messages WHERE key = 'rdv_planning'")
    
    # Mettre à jour (va créer un nouveau message)
    await update_planning_embed(bot)


class PlanningManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Annuler un RDV", style=discord.ButtonStyle.secondary, custom_id="planning_cancel_rdv_ballas")
    async def cancel_rdv(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Vérifier si l'utilisateur a un des rôles staff
        ticket_roles = [
            interaction.guild.get_role(ROLES.get("ticket_rdv")),
            interaction.guild.get_role(ROLES.get("ticket_achat")),
            interaction.guild.get_role(ROLES.get("ticket_autre")),
            interaction.guild.get_role(ROLES.get("support"))
        ]
        if not any(r in interaction.user.roles for r in ticket_roles if r):
            return await interaction.response.send_message("❌ Réservé au gang.", ephemeral=True)
        
        now_ts = int(datetime.datetime.now().timestamp())
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM rdv_planning WHERE rdv_timestamp > $1 ORDER BY rdv_timestamp LIMIT 25", now_ts - 3600)
        
        if not rows:
            return await interaction.response.send_message("Aucun RDV à annuler.", ephemeral=True)
        
        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        options = []
        for r in rows:
            u = self.bot.get_user(r['user_id'])
            dt = datetime.datetime.fromtimestamp(r['rdv_timestamp'])
            options.append(discord.SelectOption(label=f"{days[dt.weekday()]} {dt.day} {dt.hour:02d}h · {u.display_name if u else 'Inconnu'}"[:100], value=str(r['id'])))
        
        await interaction.response.send_message("Quel RDV annuler ?", view=CancelRDVView(self.bot, options), ephemeral=True)


class CancelRDVView(discord.ui.View):
    def __init__(self, bot, options):
        super().__init__(timeout=60)
        self.bot = bot
        select = discord.ui.Select(placeholder="Choisir", options=options)
        select.callback = self.callback
        self.add_item(select)
    
    async def callback(self, interaction: discord.Interaction):
        rdv_id = int(interaction.data["values"][0])
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM rdv_planning WHERE id = $1", rdv_id)
        await update_planning_embed(self.bot)
        await interaction.response.edit_message(content="✅ RDV annulé.", view=None)


class StaffRDVConfirmView(discord.ui.View):
    def __init__(self, bot, user, channel, day, hour, ts, wait_msg=None):
        super().__init__(timeout=3600)
        self.bot, self.user, self.channel, self.day, self.hour, self.ts, self.wait_msg = bot, user, channel, day, hour, ts, wait_msg

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_slot_available(self.bot, self.ts):
            return await interaction.response.send_message("❌ Créneau déjà pris.", ephemeral=True)
        await finalize_rdv(self.bot, self.channel, self.user, interaction.user, self.day, self.hour, self.ts, [self.wait_msg] if self.wait_msg else None)
        for c in self.children: c.disabled = True
        embed = discord.Embed(color=Colors.SUCCESS, description=f"✅ RDV accepté\n{self.user.name} · {format_date_french(self.day, self.hour)}")
        embed.set_footer(text="Ballas — RMB RP")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.secondary)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.wait_msg:
            try: await self.wait_msg.delete()
            except: pass
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(content="RDV refusé. Propose un autre créneau.", view=self)
        await interaction.followup.send(view=StaffCounterView(self.bot, self.user, self.channel, interaction.user))


class StaffCounterView(discord.ui.View):
    def __init__(self, bot, user, channel, staff):
        super().__init__(timeout=1800)
        self.bot, self.user, self.channel, self.staff = bot, user, channel, staff
        self.day = self.hour = None
        
        d = discord.ui.Select(placeholder="Jour", options=get_day_options())
        d.callback = self.day_cb
        self.add_item(d)
        
        h = discord.ui.Select(placeholder="Heure", options=[discord.SelectOption(label=f"{i}h00", value=f"{i}h00") for i in range(10, 24)])
        h.callback = self.hour_cb
        self.add_item(h)
    
    async def day_cb(self, i): self.day = i.data["values"][0]; await i.response.defer()
    async def hour_cb(self, i): self.hour = i.data["values"][0]; await i.response.defer()

    @discord.ui.button(label="Envoyer", style=discord.ButtonStyle.primary, row=2)
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.day or not self.hour:
            return await interaction.response.send_message("❌ Choisis jour et heure.", ephemeral=True)
        ts = get_next_rdv_timestamp(self.day, self.hour)
        if not await check_slot_available(self.bot, ts):
            return await interaction.response.send_message("❌ Créneau pris.", ephemeral=True)
        
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(content=f"✅ Proposition envoyée : {format_date_french(self.day, self.hour)}", view=self)
        
        embed = discord.Embed(color=EMBED_COLOR, description=f"{self.staff.mention} propose :\n\n**{format_date_french(self.day, self.hour)}**")
        embed.set_author(name="📅 Nouvelle proposition", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        await self.channel.send(content=self.user.mention, embed=embed, view=UserRDVResponseView(self.bot, self.user, self.channel, self.staff, self.day, self.hour, ts))


class UserRDVResponseView(discord.ui.View):
    def __init__(self, bot, user, channel, staff, day, hour, ts):
        super().__init__(timeout=None)
        self.bot, self.user, self.channel, self.staff, self.day, self.hour, self.ts = bot, user, channel, staff, day, hour, ts

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, custom_id="user_rdv_accept_ballas")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Seul le demandeur peut répondre.", ephemeral=True)
        await interaction.response.defer()
        await finalize_rdv(self.bot, self.channel, self.user, self.staff, self.day, self.hour, self.ts, [interaction.message])

    @discord.ui.button(label="Autre créneau", style=discord.ButtonStyle.secondary, custom_id="user_rdv_counter_ballas")
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Seul le demandeur peut répondre.", ephemeral=True)
        try: await interaction.message.delete()
        except: pass
        await interaction.channel.send(view=RDVSelectorView(self.bot, self.staff, None))


class RDVSelectorView(discord.ui.View):
    def __init__(self, bot, staff, proposal_msg=None):
        super().__init__(timeout=None)
        self.bot, self.staff, self.proposal_msg = bot, staff, proposal_msg
        self.day = self.hour = None
        
        d = discord.ui.Select(placeholder="Jour", options=get_day_options(), custom_id="rdv_day_select_ballas")
        d.callback = self.day_cb
        self.add_item(d)
        
        h = discord.ui.Select(placeholder="Heure", options=[discord.SelectOption(label=f"{i}h00", value=f"{i}h00") for i in range(10, 24)], custom_id="rdv_hour_select_ballas")
        h.callback = self.hour_cb
        self.add_item(h)
    
    async def day_cb(self, i): self.day = i.data["values"][0]; await i.response.defer()
    async def hour_cb(self, i): self.hour = i.data["values"][0]; await i.response.defer()

    @discord.ui.button(label="Valider", style=discord.ButtonStyle.primary, custom_id="rdv_confirm_ballas", row=2)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.day or not self.hour:
            return await interaction.response.send_message("❌ Choisis jour et heure.", ephemeral=True)
        ts = get_next_rdv_timestamp(self.day, self.hour)
        if not await check_slot_available(self.bot, ts):
            return await interaction.response.send_message(f"❌ {format_date_french(self.day, self.hour)} indisponible.", ephemeral=True)
        
        if self.proposal_msg:
            try: await self.proposal_msg.delete()
            except: pass
        try: await interaction.message.delete()
        except: pass
        await interaction.response.defer()
        
        wait_embed = discord.Embed(color=EMBED_COLOR, description=f"**{format_date_french(self.day, self.hour)}**\n\n⏳ {self.staff.mention} doit confirmer...")
        wait_embed.set_author(name="En attente", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        wait_msg = await interaction.channel.send(embed=wait_embed)
        
        try:
            staff_embed = discord.Embed(color=EMBED_COLOR, description=f"**{interaction.user.name}** demande un RDV\n\n📅 {format_date_french(self.day, self.hour)}\n📍 #{interaction.channel.name}")
            staff_embed.set_author(name="Demande de RDV", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
            await self.staff.send(embed=staff_embed, view=StaffRDVConfirmView(self.bot, interaction.user, interaction.channel, self.day, self.hour, ts, wait_msg))
        except discord.Forbidden:
            await finalize_rdv(self.bot, interaction.channel, interaction.user, self.staff, self.day, self.hour, ts, [wait_msg])


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
        
        # Rôle différent selon le type de ticket
        role_mapping = {
            "rdv": ROLES.get("ticket_rdv"),
            "achat": ROLES.get("ticket_achat"),
            "autre": ROLES.get("ticket_autre")
        }
        staff_role = guild.get_role(role_mapping.get(self.ticket_type))
        
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
        """Vérifie si l'utilisateur a un des rôles de gestion de tickets"""
        ticket_roles = [
            i.guild.get_role(ROLES.get("ticket_rdv")),
            i.guild.get_role(ROLES.get("ticket_achat")),
            i.guild.get_role(ROLES.get("ticket_autre")),
            i.guild.get_role(ROLES.get("support"))
        ]
        return any(r in i.user.roles for r in ticket_roles if r)

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

    @discord.ui.button(label="Planifier RDV", style=discord.ButtonStyle.secondary, custom_id="ticket_rdv_ballas")
    async def rdv(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._staff(interaction):
            return await interaction.response.send_message("❌ Réservé au gang.", ephemeral=True)
        embed = discord.Embed(color=EMBED_COLOR, description=f"{interaction.user.mention} te propose un RDV.\nChoisis tes disponibilités :")
        embed.set_author(name="📅 Proposition de RDV", icon_url=LOGO_URL if LOGO_URL != "a config" else None)
        msg = await interaction.channel.send(embed=embed)
        await interaction.channel.send(view=RDVSelectorView(interaction.client, interaction.user, msg))
        await interaction.response.defer()


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

    @commands.command(name="setup_planning")
    @commands.has_permissions(administrator=True)
    async def setup_planning(self, ctx):
        """Installer le planning RDV"""
        await update_planning_embed(self.bot)
        await ctx.message.add_reaction("✅")

    @commands.command(name="clear_rdv")
    @commands.has_permissions(administrator=True)
    async def clear_rdv(self, ctx):
        """Supprimer tous les RDV"""
        if not self.bot.pool:
            return await ctx.send("❌ BDD indisponible.")
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM rdv_planning")
            count = int(r.split(" ")[1]) if r else 0
        await update_planning_embed(self.bot)
        await ctx.send(f"✅ {count} RDV supprimés.")


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
