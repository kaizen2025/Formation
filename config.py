"""
Configuration pour l'application de réservation des formations Anecoop
"""

# Configuration de la base de données
DATABASE_URL = "postgresql://kwfqmcbp:qwhimeobjyxlsyuwhtyt@alpha.europe.mkdb.sh:5432/egdyfrvw"

# Configuration de l'application
APP_NAME = "Anecoop Formations"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Anecoop"
DEBUG = True

# Paramètres des formations
FORMATION_NAMES = [
    "Communiquer avec Teams",
    "Collaborer avec Teams/SharePoint",
    "Gérer les tâches d'équipe",
    "Gérer mes fichiers avec OneDrive/SharePoint"
]

# Paramètres des services
SERVICES = [
    {"id": "commerce-1", "name": "Commerce (Groupe 1)"},
    {"id": "commerce-2", "name": "Commerce (Groupe 2)"},
    {"id": "comptabilite", "name": "Comptabilité"},
    {"id": "rh-qualite-marketing", "name": "RH / Qualité / Marketing"}
]

# Paramètres des participants
MIN_PARTICIPANTS = 8
MAX_PARTICIPANTS = 12

# Mois disponibles pour les formations
AVAILABLE_MONTHS = [
    {"id": 5, "name": "Mai 2025"},
    {"id": 6, "name": "Juin 2025"}
]

# Configuration de l'envoi d'emails
EMAIL_CONFIG = {
    "smtp_server": "outlook.office365.com",
    "smtp_port": 587,
    "username": "kbivia@anecoop-france.com",
    "password": "kb3272XM&",
    "use_tls": True
}

# Mot de passe admin (à changer en production)
ADMIN_PASSWORD = "Anecoop2025"
