import os
import discord
import asyncpg
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_PRIVATE_URL") or os.getenv("POSTGRES_URL")

GUILD_ID = 1137511104487112724


class BallasBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.pool = None

    async def setup_hook(self):
        if DATABASE_URL:
            try:
                self.pool = await asyncpg.create_pool(dsn=DATABASE_URL)
                print("✅ PostgreSQL connecté")
                async with self.pool.acquire() as conn:
                    await conn.execute("CREATE TABLE IF NOT EXISTS ticket_logs (ticket_id BIGINT PRIMARY KEY, user_id BIGINT, transcript TEXT, closed_at TIMESTAMP DEFAULT NOW())")
                    await conn.execute("CREATE TABLE IF NOT EXISTS persistent_messages (key TEXT PRIMARY KEY, message_id BIGINT, channel_id BIGINT)")
                    await conn.execute("CREATE TABLE IF NOT EXISTS staff_absences (id SERIAL PRIMARY KEY, staff_id BIGINT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL, reason TEXT, created_at TIMESTAMP DEFAULT NOW())")
                    await conn.execute("CREATE TABLE IF NOT EXISTS ballas_catalog (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT, price DECIMAL(10,2) NOT NULL, category TEXT NOT NULL)")
                    await conn.execute("CREATE TABLE IF NOT EXISTS meeting_reports (id SERIAL PRIMARY KEY, message_id BIGINT UNIQUE NOT NULL, author_id BIGINT NOT NULL, report_title TEXT, attendees TEXT, promotions TEXT, reminders TEXT, other_content TEXT, created_at TIMESTAMP DEFAULT NOW())")
                    await conn.execute("CREATE TABLE IF NOT EXISTS grade_requests (id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, role_id BIGINT NOT NULL, message_id BIGINT UNIQUE, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT NOW())")
            except Exception as e:
                print(f"❌ Erreur DB: {e}")
        
        # Charger les cogs
        for ext in ["cogs.tickets", "cogs.absences", "cogs.registration", "cogs.suggestions", "cogs.tariff", "cogs.welcome", "cogs.meeting_report", "cogs.grade_request", "cogs.setup_all"]:
            try:
                await self.load_extension(ext)
                print(f"✅ {ext}")
            except Exception as e:
                print(f"⚠️ {ext}: {e}")
        
        # Sync des commandes vers le serveur
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"✅ {len(synced)} commandes synchronisées")

    async def close(self):
        if self.pool:
            await self.pool.close()
        await super().close()

    async def on_ready(self):
        print(f"💜 {self.user} connecté")
        if not self.update_status.is_running():
            self.update_status.start()

    @tasks.loop(minutes=5)
    async def update_status(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{sum(g.member_count for g in self.guilds)} membres"))

    @update_status.before_loop
    async def before_status(self):
        await self.wait_until_ready()


if __name__ == "__main__":
    if TOKEN:
        BallasBot().run(TOKEN)
    else:
        print("❌ Token manquant")
