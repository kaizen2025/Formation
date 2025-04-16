# File: config.py
"""
Configuration pour l'application de réservation des formations Anecoop
"""
import os
from werkzeug.security import generate_password_hash # Gardé ici au cas où utilisé ailleurs, mais le hash doit être dans .env

# --- AVERTISSEMENT DE SÉCURITÉ ---
# Les valeurs par défaut en clair ci-dessous (DB_URL, Mail Password)
# sont DANGEREUSES pour la production ou si le code est partagé.
# Utilisez IMPÉRATIVEMENT des variables d'environnement sécurisées.
# --- FIN AVERTISSEMENT ---

# Configuration de la base de données
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://kwfqmcbp:qwhimeobjyxlsyuwhtyt@alpha.europe.mkdb.sh:5432/egdyfrvw")

# Configuration de l'application
APP_NAME = "Anecoop Formations"
APP_VERSION = "2.1.0" # Version mise à jour
APP_AUTHOR = "Anecoop"
DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

# --- DONNÉES RETIRÉES ---
# FORMATION_MODULES, DEPARTMENTS, SERVICES, FORMATION_NAMES, AVAILABLE_MONTHS
# Ces données sont maintenant gérées via la base de données et l'interface admin.
# --- FIN DONNÉES RETIRÉES ---

# Paramètres des participants (Constants)
MIN_PARTICIPANTS = 8
MAX_PARTICIPANTS = 12

# Heures de bureau (Pour la logique de génération de créneaux)
BUSINESS_HOURS = {
    "start": 8,  # 8h00
    "end": 18,   # 18h00
    "interval": 30  # Intervalle en minutes
}

# Configuration de l'envoi d'emails
EMAIL_CONFIG = {
    "smtp_server": os.environ.get("MAIL_SERVER", "outlook.office365.com"),
    "smtp_port": int(os.environ.get("MAIL_PORT", 587)),
    "username": os.environ.get("MAIL_USERNAME", "kbivia@anecoop-france.com"),
    # !!! Ne stockez JAMAIS le mot de passe ici en production !!!
    "password": os.environ.get("MAIL_PASSWORD", "kb3272XM&"), # Utiliser variable d'env
    "use_tls": os.environ.get("MAIL_USE_TLS", "True").lower() == "true",
    "admin_emails": os.environ.get("ADMIN_EMAILS", "kbivia@anecoop-france.com").split(','),
    "templates": {
        "confirmation": {
            "subject": "Confirmation de réservation - Formation {formation_name}",
            "include_calendar": True,
            "cc_participants": True # Conserver les options de template
        },
        # Conserver les autres templates de config...
        "reminder": {
            "subject": "Rappel - Formation {formation_name} demain",
            "days_before": 1, "include_calendar": True, "cc_participants": True
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
        },
        # Nouveau template pour le lien du tableau de bord utilisateur
         "user_dashboard_link": {
             "subject": "Votre lien d'accès au tableau de bord Anecoop Formations"
         }
    }
}

# Mot de passe admin (Hash seulement)
# !!! Remplacez ceci par votre vrai hash généré et stocké dans .env !!!
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "pbkdf2:sha256:600000$...")
# Ajout Username admin pour Flask-Login
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")


# Configuration des documents (Types et Extensions)
DOCUMENT_TYPES = [
    {"id": "attachment", "name": "Pièce jointe"},
    {"id": "material", "name": "Support de cours"},
    {"id": "exercise", "name": "Exercice"},
    {"id": "reference", "name": "Document de référence"},
    {"id": "certificate", "name": "Certificat"}
]

ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf', 'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'
}
ALLOWED_EXTENSIONS = set(ALLOWED_FILE_TYPES.keys())

# Configuration du calendrier (Pour la logique JS/Backend)
CALENDAR_CONFIG = {
    "first_day": 1, "min_time": "08:00:00", "max_time": "19:00:00",
    "slot_duration": "00:30:00", "default_view": "timeGridWeek",
    "views": ["timeGridDay", "timeGridWeek", "dayGridMonth"],
    "allow_weekends": False,
    "business_hours": {
        "start": "08:00", "end": "18:00", "daysOfWeek": [1, 2, 3, 4, 5]
    },
    # Les couleurs pourraient être stockées avec les départements dans la DB
    "colors": {
        # Ces clés devront correspondre aux 'code' des départements en DB
        "commerce-1": "#2c6ecb", "commerce-2": "#2c6ecb",
        "comptabilite": "#e67e22", "rh-qualite-marketing": "#2ecc71",
        "default": "#3788d8", # Ajouter une couleur par défaut
        "selected": "#3498db"
    }
}

# Paramètres de notification (Conserver la configuration)
NOTIFICATION_CONFIG = {
    "enable_email_notifications": True, "enable_browser_notifications": True,
    "reminder_days": 1, "reminder_hours": 24, "max_notifications": 50
}

# Configuration des listes d'attente (Conserver la configuration)
WAITLIST_CONFIG = {
    "enabled": True, "auto_promote": True, "notify_on_promotion": True, "waitlist_limit": 10
}

# Configuration du tableau de bord (Conserver la configuration)
DASHBOARD_CONFIG = {
    "refresh_interval": 60000,
    "default_chart_colors": ["#2c6ecb", "#e67e22", "#2ecc71", "#e74c3c", "#9b59b6", "#f1c40f", "#1abc9c", "#34495e"],
    "enable_export": True, "default_view": "week", "items_per_page": 10
}

# Configuration des CDN et ressources externes (Conserver la configuration)
CDN_CONFIG = {
    "fontawesome": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
    "animate_css": "https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css",
    "toastify_css": "https://cdnjs.cloudflare.com/ajax/libs/toastify-js/1.12.0/toastify.min.css",
    "toastify_js": "https://cdnjs.cloudflare.com/ajax/libs/toastify-js/1.12.0/toastify.min.js",
    "fullcalendar_css": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/main.min.css",
    "fullcalendar_js": "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.9/index.global.min.js",
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    "bootstrap_js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    # Ajouter les autres CDN ici...
    "chart_js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
    "jquery": "https://code.jquery.com/jquery-3.7.1.min.js" # Si encore nécessaire
}

# Configuration des routes et du système (Conserver la configuration)
SYSTEM_CONFIG = {
    "session_timeout": 3600, "max_upload_size": 10 * 1024 * 1024,
    "temp_folder": "uploads", "log_level": "INFO", "default_language": "fr",
    # Ces routes sont conceptuelles, l'implémentation est dans app.py
    "routes": {
        "index": "/", "formations": "/formations", "participants": "/participants",
        "documents": "/documents", "confirmation": "/confirmation",
        "admin_dashboard": "/admin", "user_dashboard": "/user_dashboard"
    }
}
