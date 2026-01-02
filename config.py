import discord

# --- CONFIGURATION VISUELLE ---
EMBED_COLOR = 0x800080  # Violet (couleur des Ballas)

# Logo Ballas
LOGO_URL = "a config"

# Bannière (thumbnail sur panneaux principaux)
BANNER_URL = "a config"

# --- SALONS ---
CHANNELS = {
    "tickets_panel": "a config",
    "tickets_category": "a config",
    "tickets_logs": "a config",
    "absences": "a config",
    "suggestions": "a config",
    "registration": 1137518581291171941,
    "welcome": "a config",
    "tarif": "a config",
    "meeting_report": "a config",
    "announcements": "a config",
    "grade_requests": "a config",  # Salon pour les demandes de grade
    "project": 1137513227002069132,
}

# --- RÔLES ---
ROLES = {
    "support": "a config",
    "super_admin": "a config",
    "recrutement": "a config",
    "citoyen": "a config",
    "tarif_manager": "a config",
    "report_validator": "a config",
}

GUILD_ID = 1137511104487112724

# --- FONCTIONS ---
def create_embed(title: str = None, description: str = None) -> discord.Embed:
    embed = discord.Embed(description=description, color=EMBED_COLOR)
    if title:
        if LOGO_URL and LOGO_URL != "a config":
            embed.set_author(name=title, icon_url=LOGO_URL)
        else:
            embed.set_author(name=title)
    embed.set_footer(text="Ballas — RMB RP")
    return embed

# Couleurs pour les états
class Colors:
    PRIMARY = 0x800080
    SUCCESS = 0x58D68D
    ERROR = 0xEC7063
    WARNING = 0xF4D03F
    MUTED = 0x99A3A4
