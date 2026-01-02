import discord

# --- CONFIGURATION VISUELLE ---
EMBED_COLOR = 0x800080  # Violet (couleur des Ballas)

# Logo Ballas
LOGO_URL = "https://cdn.discordapp.com/attachments/1443995816233664606/1456655396973445314/Ballas.png"

# Bannière (thumbnail sur panneaux principaux)
BANNER_URL = "https://cdn.discordapp.com/attachments/1443995816233664606/1456655396973445314/Ballas.png"

# --- SALONS ---
CHANNELS = {
    "tickets_panel": 1456657984846303324,
    "tickets_category": 1137511728658255993,
    "tickets_logs": 1456658356088606761,
    "rdv_planning": 1456659575250882641,         # Salon pour afficher le planning des RDV
    "absences": 1456660099824353455,
    "suggestions": 1456660199178764561,
    "registration": 1137518581291171941,
    "welcome": 1137511105279832093,
    "tarif": "a config",
    "meeting_report": 1456660524673667233,
    "announcements": 1456660887980081473,
    "grade_requests": 1456661043731501056,       # Salon pour les demandes de grade
    "project": 1137513227002069132,
}

# --- RÔLES ---
ROLES = {
    "support": 1456668708599500987,              # Rôle staff général (gestion absences, grades, etc.)
    "super_admin": 1456668708599500987,          # Administrateur
    "citoyen": 1450663368959590420,              # Rôle donné après enregistrement
    "tarif_manager": 1137518847327485952,        # Peut gérer le catalogue
    "report_validator": 1137518847327485952,     # Peut valider les comptes rendus
    
    # Rôles par catégorie de ticket
    "ticket_rdv": 1456661487253979299,           # Notifié pour les tickets Rendez-vous
    "ticket_achat": 1456661605969301504,         # Notifié pour les tickets Achat
    "ticket_autre": 1456661666564669451,         # Notifié pour les tickets Autre
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
