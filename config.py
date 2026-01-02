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
    "rdv_planning": 1456659575250882641,
    "absences": 1456660099824353455,
    "suggestions": 1456660199178764561,
    
    # --- MODIFICATION ICI ---
    # Le panneau "S'enregistrer" sera ici :
    "registration": 1456661043731501056,
    
    # Le panneau "Demande de grade" sera ici :
    "grade_requests": 1137518581291171941,
    
    # TOUTES les demandes (validations staff) arrivent ici :
    "requests_validation": 1456674238126887046,
    # ------------------------

    "welcome": 1137511105279832093,
    "tarif": 1456666034156339251,
    "meeting_report": 1456660524673667233,
    "announcements": 1456660887980081473,
    "project": 1137513227002069132,
}

# --- RÔLES ---
ROLES = {
    "support": 1456668708599500987,              # Rôle staff général
    "super_admin": 1456668708599500987,          # Administrateur
    "citoyen": 1450663368959590420,              # Rôle donné après enregistrement
    "tarif_manager": 1137518847327485952,        # Peut gérer le catalogue
    "report_validator": 1137518847327485952,     # Peut valider les comptes rendus
    
    "ticket_rdv": 1456661487253979299,
    "ticket_achat": 1456661605969301504,
    "ticket_autre": 1456661666564669451,
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

class Colors:
    PRIMARY = 0x800080
    SUCCESS = 0x58D68D
    ERROR = 0xEC7063
    WARNING = 0xF4D03F
    MUTED = 0x99A3A4
