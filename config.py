# File: config.py
"""
Configuration pour l'application de réservation des formations Anecoop
"""
import os
from werkzeug.security import generate_password_hash

# Configuration de la base de données
# It's better to use environment variables for sensitive data like DB URLs
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://kwfqmcbp:qwhimeobjyxlsyuwhtyt@alpha.europe.mkdb.sh:5432/egdyfrvw")

# Configuration de l'application
APP_NAME = "Anecoop Formations"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Anecoop"
# DEBUG should ideally be False in production, controlled by environment variable
DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

# Paramètres des formations (renommé en modules)
FORMATION_MODULES = [
    {
        "id": "teams-communication",
        "name": "Communiquer avec Teams",
        "description": "Apprendre à utiliser Microsoft Teams pour la communication d'équipe",
        "duration_minutes": 90
    },
    {
        "id": "teams-sharepoint",
        "name": "Collaborer avec Teams/SharePoint",
        "description": "Utiliser Teams et SharePoint pour la collaboration documentaire",
        "duration_minutes": 90
    },
    {
        "id": "task-management",
        "name": "Gérer les tâches d'équipe",
        "description": "Maîtriser les outils de gestion des tâches d'équipe",
        "duration_minutes": 90
    },
    {
        "id": "onedrive-sharepoint",
        "name": "Gérer mes fichiers avec OneDrive/SharePoint",
        "description": "Organisation et gestion efficace des fichiers",
        "duration_minutes": 90
    }
]

# Paramètres des départements (anciennement services)
DEPARTMENTS = [
    {
        "id": "commerce-1",
        "name": "Commerce (Groupe 1)",
        "description": "Premier groupe du département Commerce",
        "max_groups": 1
    },
    {
        "id": "commerce-2",
        "name": "Commerce (Groupe 2)",
        "description": "Second groupe du département Commerce",
        "max_groups": 1
    },
    {
        "id": "comptabilite",
        "name": "Comptabilité",
        "description": "Département Comptabilité",
        "max_groups": 1
    },
    {
        "id": "rh-qualite-marketing",
        "name": "RH / Qualité / Marketing",
        "description": "Départements RH, Qualité et Marketing",
        "max_groups": 1
    }
]

# Pour compatibilité avec le code existant
SERVICES = DEPARTMENTS
FORMATION_NAMES = [module["name"] for module in FORMATION_MODULES]

# Paramètres des participants
MIN_PARTICIPANTS = 8
MAX_PARTICIPANTS = 12

# Mois disponibles pour les formations
AVAILABLE_MONTHS = [
    {"id": 5, "name": "Mai 2025"},
    {"id": 6, "name": "Juin 2025"}
]

# Heures de bureau (horaires disponibles pour les formations)
BUSINESS_HOURS = {
    "start": 8,  # 8h00
    "end": 18,   # 18h00
    "interval": 30  # Intervalle en minutes
}

# Configuration de l'envoi d'emails (Use environment variables!)
EMAIL_CONFIG = {
    "smtp_server": os.environ.get("MAIL_SERVER", "outlook.office365.com"),
    "smtp_port": int(os.environ.get("MAIL_PORT", 587)),
    "username": os.environ.get("MAIL_USERNAME", "kbivia@anecoop-france.com"),
    "password": os.environ.get("MAIL_PASSWORD", "kb3272XM&"), # STORE THIS SECURELY
    "use_tls": os.environ.get("MAIL_USE_TLS", "True").lower() == "true",
    # Adresses email pour les notifications internes
    "admin_emails": os.environ.get("ADMIN_EMAILS", "kbivia@anecoop-france.com").split(','),
    # Templates d'email
    "templates": {
        "confirmation": {
            "subject": "Confirmation de réservation - Formation {formation_name}",
            "include_calendar": True,
            "cc_participants": True
        },
        "reminder": {
            "subject": "Rappel - Formation {formation_name} demain",
            "days_before": 1,
            "include_calendar": True,
            "cc_participants": True
        },
        "waitlist": {
            "subject": "Inscription en liste d'attente - Formation {formation_name}",
            "include_details": True
        },
        "waitlist_confirmation": {
            "subject": "Place disponible - Formation {formation_name}",
            "include_calendar": True
        },
        "document_notification": {
            "subject": "Nouveau document disponible - Formation {formation_name}",
            "include_download_link": True
        }
    }
}

# Mot de passe admin (Hash the password!)
# Generate a hash for your desired password, e.g., using:
# from werkzeug.security import generate_password_hash
# print(generate_password_hash('YourSecurePassword'))
# Store the *hash* here, not the plain text password.
# Example hash for 'Anecoop2025':
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "pbkdf2:sha256:600000$key...") # Replace with your actual hash

# Configuration des documents
DOCUMENT_TYPES = [
    {"id": "attachment", "name": "Pièce jointe"},
    {"id": "material", "name": "Support de cours"},
    {"id": "exercise", "name": "Exercice"},
    {"id": "reference", "name": "Document de référence"},
    {"id": "certificate", "name": "Certificat"}
]

# Types de fichiers autorisés pour les uploads
ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png'
}
ALLOWED_EXTENSIONS = set(ALLOWED_FILE_TYPES.keys()) # Derive from ALLOWED_FILE_TYPES

# Configuration du calendrier
CALENDAR_CONFIG = {
    "first_day": 1,  # 0=dimanche, 1=lundi
    "min_time": "08:00:00",
    "max_time": "19:00:00",
    "slot_duration": "00:30:00",
    "default_view": "timeGridWeek",
    "views": ["timeGridDay", "timeGridWeek", "dayGridMonth"],
    "allow_weekends": False,
    "business_hours": {
        "start": "08:00",
        "end": "18:00",
        "daysOfWeek": [1, 2, 3, 4, 5]  # lundi à vendredi
    },
    "colors": {
        "commerce-1": "#2c6ecb",
        "commerce-2": "#2c6ecb",
        "comptabilite": "#e67e22",
        "rh-qualite-marketing": "#2ecc71",
        "selected": "#3498db"
    }
}

# Paramètres de notification
NOTIFICATION_CONFIG = {
    "enable_email_notifications": True,
    "enable_browser_notifications": True,
    "reminder_days": 1,  # Jours avant la formation pour envoyer un rappel
    "reminder_hours": 24,  # Heures avant la formation pour envoyer un rappel
    "max_notifications": 50  # Nombre maximal de notifications à conserver par utilisateur
}

# Configuration des listes d'attente
WAITLIST_CONFIG = {
    "enabled": True,  # Activer/désactiver les listes d'attente
    "auto_promote": True,  # Promouvoir automatiquement les personnes en liste d'attente si une place se libère
    "notify_on_promotion": True,  # Envoyer une notification en cas de promotion
    "waitlist_limit": 10  # Limite de personnes en liste d'attente par formation
}

# Configuration du tableau de bord
DASHBOARD_CONFIG = {
    "refresh_interval": 60000,  # Intervalle de rafraîchissement en millisecondes (1 minute)
    "default_chart_colors": ["#2c6ecb", "#e67e22", "#2ecc71", "#e74c3c", "#9b59b6", "#f1c40f", "#1abc9c", "#34495e"],
    "enable_export": True,  # Activer l'export des données (PDF, Excel, etc.)
    "default_view": "week",  # Vue par défaut (jour, semaine, mois)
    "items_per_page": 10  # Nombre d'éléments par page pour les tableaux
}

# Configuration des CDN et ressources externes
CDN_CONFIG = {
    "fontawesome": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
    "animate_css": "https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css",
    "toastify_css": "https://cdnjs.cloudflare.com/ajax/libs/toastify-js/1.12.0/toastify.min.css",
    "toastify_js": "https://cdnjs.cloudflare.com/ajax/libs/toastify-js/1.12.0/toastify.min.js",
    "fullcalendar_css": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/main.min.css",
    "fullcalendar_js": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js", # Use index.global.min.js
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "bootstrap_js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    "jspdf": "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
    "html2canvas": "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
    "jszip": "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js",
    "papaparse": "https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js",
    "xlsx": "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js",
    "chart_js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
    "tippy_js": "https://cdn.jsdelivr.net/npm/tippy.js@6.3.7/dist/tippy-bundle.umd.min.js",
    "tippy_css": "https://cdn.jsdelivr.net/npm/tippy.js@6.3.7/dist/tippy.css",
    "tippy_theme": "https://cdn.jsdelivr.net/npm/tippy.js@6.3.7/themes/light-border.css",
    "jquery": "https://code.jquery.com/jquery-3.7.1.min.js"
}

# Configuration des routes et du système
SYSTEM_CONFIG = {
    "session_timeout": 3600,  # Durée de la session en secondes (1 heure)
    "max_upload_size": 10 * 1024 * 1024,  # 10 MB
    "temp_folder": "uploads",  # Dossier temporaire pour les uploads
    "log_level": "INFO",  # Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    "default_language": "fr",  # Langue par défaut
    "routes": {
        "index": "/",
        "formations": "/formations",
        "participants": "/participants",
        "documents": "/documents",
        "confirmation": "/confirmation",
        "admin_dashboard": "/admin",
        "user_dashboard": "/user_dashboard"
    }
}