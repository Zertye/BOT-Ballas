# 💜 Bot Ballas — RMB RP

Bot Discord pour le gang des Ballas.

## Fonctionnalités

- Tickets (Rendez-vous, Achat, Autre)
- Absences du personnel
- Grille tarifaire (catalogue)
- Suggestions
- Bienvenue automatique
- Enregistrement
- Compte rendu de réunion
- Demande de grade

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env  # Configurer TOKEN + DATABASE_URL
python main.py
```

## Configuration

Avant de lancer le bot, configure le fichier `config.py` :

1. Remplace tous les `"a config"` par les IDs correspondants
2. Configure les URLs du logo et bannière
3. Vérifie les IDs des rôles et salons

## Commandes

### ⚡ Commandes Slash

| Commande | Description |
|----------|-------------|
| `/setup_all` | Configurer tous les panneaux |
| `/add_article` | Ajouter un article au catalogue |
| `/remove_article` | Retirer un article du catalogue |
| `/modif_article` | Modifier un article |
| `/help` | Afficher toutes les commandes |

### 🔧 Commandes Préfixées (!)

| Commande | Description |
|----------|-------------|
| `!sync` | Resynchroniser les commandes |
| `!status` | Voir le statut du bot |
| `!reset_panels` | Réinitialiser tous les panneaux |
| `!setup_tickets` | Installer le panneau tickets |
| `!setup_absences` | Installer le panneau absences |
| `!setup_registration` | Installer le panneau enregistrement |
| `!setup_suggestions` | Installer le panneau suggestions |
| `!setup_report` | Installer le panneau compte rendu |
| `!setup_grade` | Installer le panneau demande de grade |
| `!clear_absences` | Supprimer toutes les absences |
| `!clear_grades` | Supprimer les demandes de grade en attente |
| `!test_rapport` | Tester le rapport hebdomadaire |
| `!refresh_tarifs` | Rafraîchir l'affichage des tarifs |
| `!info_article <nom>` | Voir les détails d'un article |
| `!welcome [@membre]` | Tester le message de bienvenue |

## Structure

```
ballas_bot/
├── main.py
├── config.py
├── requirements.txt
├── README.md
└── cogs/
    ├── __init__.py
    ├── tickets.py
    ├── absences.py
    ├── registration.py
    ├── suggestions.py
    ├── tariff.py
    ├── welcome.py
    ├── meeting_report.py
    ├── grade_request.py
    └── setup_all.py
```

## Catégories de Tickets

- **Rendez-vous** : Demande de RDV avec pseudo, objet et disponibilités
- **Achat** : Demande d'achat avec pseudo, article, quantité et infos complémentaires
- **Autre** : Demande générale avec pseudo et description

## Catégories de Produits

- 🔫 Armes
- 💊 Drogues
- 🚗 Véhicules
- 💼 Services
- 📦 Divers

## Demande de Grade

Les membres peuvent demander un grade via le panneau dédié. Limite de 2 demandes simultanées par membre. Les hauts-gradés peuvent accepter ou refuser les demandes.
