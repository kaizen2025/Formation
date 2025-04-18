=== Local GitIngest - Analyse de . ===

Résumé:
Répertoire: .
Fichiers analysés: 33
Tokens estimés: 247.8k

Structure des répertoires:
└── Formation/
├── .env
├── app.py
├── config.py
├── dockerfile
├── local_gitingest.py
├── models.py
├── readme.md
├── render.yaml
├── requirements.txt
├── routes.py
├── services.py
├── setup.py
├── utils.py
├── static/
│   ├── css/
│   │   ├── admin-dark.css
│   │   ├── admin.css
│   │   ├── dark-mode.css
│   │   ├── style.css
│   ├── img/
│   ├── js/
│   │   ├── admin.js
│   │   ├── main.js
│   ├── uploads/
├── templates/
│   ├── calendar.html
│   ├── documents.html
│   ├── index.html
│   ├── layout.html
│   ├── propose_time.html
│   ├── service_details.html
│   ├── track_proposal.html
│   ├── training_details.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── edit_training.html
│   │   ├── layout.html
│   │   ├── login.html
│   │   ├── trainings.html
│   ├── errors/
│   │   ├── 403.html
│   │   ├── 404.html
│   │   ├── 500.html


Contenu des fichiers:

FICHIER: .env
# Configuration générale
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=anecoopFormationsBooking2025SecretKey

# Configuration base de données
DATABASE_URL=postgresql://khoiffzx:jagtqaxjqdwxkyxklzjw@alpha.europe.mkdb.sh:5432/wypdrdri

# Configuration email
MAIL_SERVER=outlook.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=kbivia@anecoop-france.com
MAIL_PASSWORD=kb3272XM&
MAIL_DEFAULT_SENDER=kbivia@anecoop-france.com

# Configuration admin
ADMIN_PASSWORD=Anecoop2025

# Configuration application
APP_NAME=Anecoop Formations
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max upload size
SESSION_LIFETIME=1440  # 24 heures en minutes

# Configuration Render
RENDER_EXTERNAL_URL=https://anecoop-formations.onrender.com

FICHIER: app.py
"""
Point d'entrée principal de l'application Flask pour le système de réservation Anecoop.
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from config import get_config
from models import db
from routes import register_blueprints
from services import mail, initialize_database, send_weekly_summary_to_admin

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    """Crée et configure l'application Flask."""
    app = Flask(__name__)
    
    # Chargement de la configuration
    app.config.from_object(get_config())
    
    # Activer le rechargement automatique des templates
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Initialisation des extensions
    db.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)
    
    # Enregistrement des blueprints
    register_blueprints(app)
    
    # Gestion des erreurs
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    # Contexte global pour les templates
    @app.context_processor
    def utility_processor():
        return {
            'app_name': app.config['APP_NAME'],
            'current_year': datetime.utcnow().year
        }
    
    # Initialisation de la base de données
    with app.app_context():
        initialize_database()
    
    # Configuration du planificateur de tâches
    scheduler = BackgroundScheduler()
    
    # Ajouter la tâche d'envoi du résumé hebdomadaire (chaque lundi à 8h)
    @scheduler.scheduled_job('cron', day_of_week='mon', hour=8)
    def send_weekly_summary():
        with app.app_context():
            logger.info("Envoi du résumé hebdomadaire")
            send_weekly_summary_to_admin()
    
    # Démarrer le planificateur
    scheduler.start()
    
    logger.info(f"Application initialisée en mode: {config_name}")
    return app


# Créer l'application
app = create_app()


# Point d'entrée pour l'exécution directe
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)  # Activer le mode debug pour le développement

FICHIER: config.py
"""
Configuration de l'application Flask pour le système de réservation Anecoop.
Ce module charge les variables d'environnement et configure l'application.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

class Config:
    """Configuration de base pour l'application."""
    # Configuration générale
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-key-change-in-production')
    APP_NAME = os.getenv('APP_NAME', 'Anecoop Formations')
    
    # Configuration de la base de données
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuration du serveur de mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'outlook.office365.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Configuration admin
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Anecoop2025')
    
    # Configuration des téléchargements
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB par défaut
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip'}
    
    # Configuration des sessions
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv('SESSION_LIFETIME', 1440)))
    
    # Configuration des services et formations
    SERVICES = {
        'comptabilite': {
            'name': 'Comptabilité',
            'color': '#4285F4',  # Bleu
            'manager': 'Lisa VAN SCHOORISSE',
            'email': 'lvanschoorisse@anecoop-france.com'
        },
        'florensud': {
            'name': 'Florensud',
            'color': '#34A853',  # Vert
            'manager': 'Antoine LAMY',
            'email': 'a.lamy@florensud.fr'
        },
        'commerce': {
            'name': 'Commerce Anecoop-Solagora',
            'color': '#FBBC05',  # Jaune
            'manager': 'Andreu MIR SOLAGORA',
            'email': 'amir@solagora.com'
        },
        'qualite': {
            'name': 'Qualité',
            'color': '#EA4335',  # Rouge
            'manager': 'Elodie PHILIBERT',
            'email': 'ephilibert@anecoop-france.com'
        },
        'marketing': {
            'name': 'Marketing',
            'color': '#9C27B0',  # Violet
            'manager': 'Camille BROUSSOUX',
            'email': 'cbroussoux@anecoop-france.com'
        },
        'rh': {
            'name': 'RH',
            'color': '#FF9800',  # Orange
            'manager': 'Elisabeth GOMEZ',
            'email': 'egomez@anecoop-france.com'
        }
    }
    
    TRAININGS = [
        {
            'id': 'teams-communication',
            'name': 'Communiquer avec Teams',
            'duration': 90,  # en minutes
            'description': 'Apprenez à utiliser Microsoft Teams pour communiquer efficacement avec vos collègues.'
        },
        {
            'id': 'teams-sharepoint',
            'name': 'Collaborer avec Teams/SharePoint',
            'duration': 90,
            'description': 'Découvrez comment collaborer sur des documents avec Teams et SharePoint.'
        },
        {
            'id': 'tasks-management',
            'name': 'Gérer les tâches d\'équipe',
            'duration': 90,
            'description': 'Maîtrisez la gestion des tâches d\'équipe avec les outils Microsoft.'
        },
        {
            'id': 'onedrive-sharepoint',
            'name': 'Gérer mes fichiers avec OneDrive/SharePoint',
            'duration': 90,
            'description': 'Apprenez à organiser et partager vos fichiers avec OneDrive et SharePoint.'
        }
    ]


class DevelopmentConfig(Config):
    """Configuration pour l'environnement de développement."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configuration pour l'environnement de production."""
    DEBUG = False
    TESTING = False
    # En production, forcer HTTPS
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Configuration pour les tests."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Configuration selon l'environnement
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

# Configuration active
def get_config():
    """Récupère la configuration active selon l'environnement."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name[env]

FICHIER: dockerfile
FROM python:3.11-slim

# Définir un répertoire de travail
WORKDIR /app

# Installer les dépendances nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Créer un répertoire pour les uploads s'il n'existe pas
RUN mkdir -p static/uploads

# Exposer le port
EXPOSE 8000

# Définir les variables d'environnement
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Commande pour démarrer l'application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]


FICHIER: models.py
"""
Modèles de données pour le système de réservation Anecoop.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
import uuid

db = SQLAlchemy()

def generate_uuid():
    """Génère un UUID unique pour les identifiants."""
    return str(uuid.uuid4())


class Service(db.Model):
    """Modèle représentant un service de l'entreprise."""
    __tablename__ = 'services'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager_name = db.Column(db.String(100), nullable=False)
    manager_email = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    trainings = db.relationship('Training', backref='service', lazy=True)
    groups = db.relationship('Group', backref='service', lazy=True)

    def __repr__(self):
        return f'<Service {self.name}>'


class Training(db.Model):
    """Modèle représentant une formation disponible."""
    __tablename__ = 'trainings'

    id = db.Column(db.String(50), primary_key=True)
    service_id = db.Column(db.String(50), db.ForeignKey('services.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Integer, default=90)  # Durée en minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    sessions = db.relationship('Session', backref='training', lazy=True)
    documents = db.relationship('Document', backref='training', lazy=True)

    def __repr__(self):
        return f'<Training {self.name}>'


class Group(db.Model):
    """Modèle représentant un groupe de participants."""
    __tablename__ = 'groups'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    service_id = db.Column(db.String(50), db.ForeignKey('services.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    min_participants = db.Column(db.Integer, default=8)
    max_participants = db.Column(db.Integer, default=12)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    participants = db.relationship('Participant', backref='group', lazy=True)
    sessions = db.relationship('Session', backref='group', lazy=True)

    def __repr__(self):
        return f'<Group {self.name}>'


class Participant(db.Model):
    """Modèle représentant un participant à une formation."""
    __tablename__ = 'participants'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), default=generate_uuid)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    attendances = db.relationship('Attendance', backref='participant', lazy=True)

    def __repr__(self):
        return f'<Participant {self.name}>'


class Session(db.Model):
    """Modèle représentant une session de formation."""
    __tablename__ = 'sessions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    training_id = db.Column(db.String(50), db.ForeignKey('trainings.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    attendances = db.relationship('Attendance', backref='session', lazy=True)
    proposals = db.relationship('TimeProposal', backref='session', lazy=True)

    def __repr__(self):
        return f'<Session {self.id} - {self.start_time}>'


class Attendance(db.Model):
    """Modèle représentant la présence d'un participant à une session."""
    __tablename__ = 'attendances'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    participant_id = db.Column(db.String(36), db.ForeignKey('participants.id'), nullable=False)
    status = db.Column(db.String(20), default='registered')  # registered, attended, absent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Attendance {self.id}>'


# Extrait du fichier models.py - Correction de la relation TimeProposal

class TimeProposal(db.Model):
    """Modèle représentant une proposition de créneau par un utilisateur."""
    __tablename__ = 'time_proposals'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=True)
    training_id = db.Column(db.String(50), db.ForeignKey('trainings.id'), nullable=False)
    proposer_email = db.Column(db.String(100), nullable=False)
    proposer_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    proposed_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation correctement définie avec Training - ajoutez ces lignes
    training = db.relationship('Training', backref='proposals', lazy='joined')

    def __repr__(self):
        return f'<TimeProposal {self.id} - {self.proposed_time}>'


class Document(db.Model):
    """Modèle représentant un document partagé pour une formation."""
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    training_id = db.Column(db.String(50), db.ForeignKey('trainings.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Taille en octets
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    downloads = db.relationship('DocumentDownload', backref='document', lazy=True)

    def __repr__(self):
        return f'<Document {self.name}>'


class DocumentDownload(db.Model):
    """Modèle représentant le téléchargement d'un document par un utilisateur."""
    __tablename__ = 'document_downloads'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    user_name = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DocumentDownload {self.id}>'


class AuditLog(db.Model):
    """Modèle représentant un journal d'audit pour les actions importantes."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False)
    user_email = db.Column(db.String(100), nullable=True)
    user_ip = db.Column(db.String(50), nullable=True)
    changes = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action} - {self.entity_type}>'

FICHIER: render.yaml
services:
  - type: web
    name: anecoop-formations
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: anecoop-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
      - key: MAIL_SERVER
        value: outlook.office365.com
      - key: MAIL_PORT
        value: 587
      - key: MAIL_USE_TLS
        value: True
      - key: MAIL_USERNAME
        sync: false
      - key: MAIL_PASSWORD
        sync: false
      - key: MAIL_DEFAULT_SENDER
        sync: false
      - key: ADMIN_PASSWORD
        sync: false
    autoDeploy: true
    healthCheckPath: /

databases:
  - name: anecoop-db
    databaseName: anecoop_formations
    plan: starter


FICHIER: requirements.txt
# Web framework and extensions
Flask>=3.0.3  # Latest stable version, improved async support
Flask-SQLAlchemy>=3.1.1  # Latest, compatible with Flask 3.0
Flask-Migrate>=4.0.7  # Latest, supports SQLAlchemy 2.x
Flask-Mailman>=1.0.0  # Modern replacement for Flask-Mail

# Database connector
psycopg[binary]>=3.2.1  # Modern alternative to psycopg2, better Python 3.13 support

# Environment and utilities
python-dotenv>=1.0.1  # Latest, minor update
Werkzeug>=3.0.3  # Latest, compatible with Flask 3.0
Jinja2>=3.1.4  # Latest, minor update
gunicorn>=22.0.0  # Latest, improved performance

# Scheduling and calendar
APScheduler>=3.10.5  # Latest, minor update
icalendar>=5.0.13  # Latest, bug fixes
pytz>=2024.2  # Latest, updated timezone data

# Email validation
email-validator>=2.2.0  # Latest, improved validation

# Testing
pytest>=8.3.3  # Latest, improved features
pytest-flask>=1.3.0  # Latest, compatible with Flask 3.0
python-slugify

FICHIER: routes.py
"""
Routes pour le système de réservation Anecoop.
Ce module contient toutes les routes de l'application.
"""

import os
import flask
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    jsonify, flash, session, send_from_directory, current_app, abort
)
from werkzeug.utils import secure_filename
from sqlalchemy import func
from models import (
    db, Service, Training, Group, Participant, Session as TrainingSession,
    Attendance, TimeProposal, Document, DocumentDownload
)
from services import (
    login_required, authenticate_admin, logout_admin, create_time_proposal,
    approve_time_proposal, reject_time_proposal, save_document, log_document_download,
    initialize_database, send_weekly_summary_to_admin, log_audit_event
)

# Création des blueprints
main = Blueprint('main', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')
api = Blueprint('api', __name__, url_prefix='/api')


# Routes principales
@main.route('/')
def index():
    """Page d'accueil."""
    services = Service.query.all()
    return render_template('index.html', services=services)


@main.route('/services')
def services():
    """Liste des services."""
    services = Service.query.all()
    return render_template('services.html', services=services)


@main.route('/service/<service_id>')
def service_details(service_id):
    """Détails d'un service."""
    # Récupérer le service
    service = Service.query.get_or_404(service_id)
    
    # Récupérer toutes les formations du service
    trainings = Training.query.filter_by(service_id=service_id).all()
    
    # Récupérer le nombre de sessions à venir par formation
    upcoming_sessions_counts = {}
    for training in trainings:
        count = TrainingSession.query.filter_by(
            training_id=training.id,
            status='scheduled'
        ).filter(
            TrainingSession.start_time > datetime.utcnow()
        ).count()
        upcoming_sessions_counts[training.id] = count
    
    return render_template(
        'service_details.html', 
        service=service, 
        trainings=trainings,
        upcoming_sessions_counts=upcoming_sessions_counts
    )


@main.route('/trainings')
def trainings():
    """Liste des formations."""
    trainings = Training.query.all()
    return render_template('trainings.html', trainings=trainings)


@main.route('/training/<training_id>')
def training_details(training_id):
    """Détails d'une formation."""
    # Récupérer la formation avec les relations
    training = Training.query.options(
        db.joinedload(Training.service),
        db.joinedload(Training.sessions)
    ).get_or_404(training_id)
    
    # Récupérer les sessions à venir
    upcoming_sessions = TrainingSession.query.filter_by(
        training_id=training_id,
        status='scheduled'
    ).filter(
        TrainingSession.start_time > datetime.utcnow()
    ).order_by(TrainingSession.start_time).all()
    
    # Récupérer les documents publics
    documents = Document.query.filter_by(
        training_id=training_id,
        is_public=True
    ).all()
    
    # Récupérer le nombre de personnes ayant déjà participé ou inscrites
    participants_count = db.session.query(func.count(Attendance.id)).join(
        TrainingSession
    ).filter(
        TrainingSession.training_id == training_id
    ).scalar()
    
    return render_template(
        'training_details.html',
        training=training,
        upcoming_sessions=upcoming_sessions,
        documents=documents,
        participants_count=participants_count
    )


@main.route('/training/<training_id>/sessions')
def training_sessions(training_id):
    """Sessions d'une formation."""
    training = Training.query.get_or_404(training_id)
    sessions = TrainingSession.query.filter_by(training_id=training_id).order_by(TrainingSession.start_time).all()
    return render_template('training_sessions.html', training=training, sessions=sessions)


@main.route('/training/<training_id>/propose', methods=['GET', 'POST'])
def propose_time(training_id):
    """Proposition d'un créneau pour une formation."""
    training = Training.query.get_or_404(training_id)
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        email = request.form.get('email')
        name = request.form.get('name')
        department = request.form.get('department')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        # Valider les entrées
        if not all([email, name, date_str, time_str]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('propose_time.html', training=training)
        
        try:
            # Convertir la date et l'heure en datetime
            date_parts = date_str.split('/')
            date = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            time_parts = time_str.split(':')
            proposed_time = date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            
            # Vérifier que la date est dans le futur
            if proposed_time <= datetime.utcnow():
                flash('La date proposée doit être dans le futur.', 'danger')
                return render_template('propose_time.html', training=training)
            
            # Créer la proposition
            success, result = create_time_proposal(training_id, email, name, department, proposed_time)
            
            if success:
                flash('Votre proposition a été enregistrée. Vous recevrez un email de confirmation.', 'success')
                return redirect(url_for('main.training_details', training_id=training_id))
            else:
                flash(f'Une erreur est survenue: {result}', 'danger')
        except Exception as e:
            flash(f'Format de date ou heure invalide: {str(e)}', 'danger')
    
    return render_template('propose_time.html', training=training)


@main.route('/track/<token>')
def track_proposal(token):
    """Suivi d'une proposition de créneau."""
    # Rechercher la proposition avec le token dans les notes
    proposal = TimeProposal.query.filter(
        TimeProposal.notes.like(f"%Token de suivi: {token}%")
    ).first_or_404()
    
    return render_template('track_proposal.html', proposal=proposal)


@main.route('/documents')
def documents():
    """Liste des documents publics."""
    documents = Document.query.filter_by(is_public=True).all()
    services = Service.query.all()
    trainings = Training.query.all()
    return render_template('documents.html', documents=documents, services=services, trainings=trainings)


@main.route('/document/<document_id>')
def document_details(document_id):
    """Détails d'un document."""
    document = Document.query.get_or_404(document_id)
    
    # Vérifier si le document est public
    if not document.is_public and 'admin_logged_in' not in session:
        abort(403)
    
    return render_template('document_details.html', document=document)


@main.route('/document/<document_id>/download')
def download_document(document_id):
    """Téléchargement d'un document."""
    document = Document.query.get_or_404(document_id)
    
    # Vérifier si le document est public
    if not document.is_public and 'admin_logged_in' not in session:
        abort(403)
    
    # Récupérer l'email de l'utilisateur si disponible
    user_email = request.args.get('email')
    user_name = request.args.get('name')
    
    # Enregistrer le téléchargement
    if user_email:
        log_document_download(document_id, user_email, user_name)
    
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        document.file_path,
        as_attachment=True,
        download_name=document.name
    )


@main.route('/calendar')
def calendar():
    """Calendrier des sessions."""
    # Récupérer tous les services pour le filtre
    services = Service.query.all()
    
    # Récupérer la date de début et de fin pour le calendrier
    start_date = request.args.get('start', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date = request.args.get('end', (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'))
    
    # Convertir les dates
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Récupérer les sessions dans cette période avec les relations
    sessions = TrainingSession.query.join(Training).join(Service).filter(
        TrainingSession.start_time >= start_date,
        TrainingSession.start_time <= end_date,
        TrainingSession.status != 'cancelled'  # Exclure les sessions annulées
    ).all()
    
    return render_template('calendar.html', 
                         sessions=sessions, 
                         start_date=start_date, 
                         end_date=end_date,
                         services=services)


# Routes d'administration
@admin.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion d'administration."""
    if request.method == 'POST':
        password = request.form.get('password')
        
        if authenticate_admin(password):
            flash('Connexion réussie.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Mot de passe incorrect.', 'danger')
    
    return render_template('admin/login.html')


@admin.route('/logout')
@login_required
def logout():
    """Déconnexion d'administration."""
    logout_admin()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('main.index'))


@admin.route('/')
@login_required
def dashboard():
    """Tableau de bord d'administration."""
    # Statistiques
    stats = {
        'services': Service.query.count(),
        'trainings': Training.query.count(),
        'groups': Group.query.count(),
        'participants': Participant.query.count(),
        'sessions': TrainingSession.query.count(),
        'documents': Document.query.count(),
        'pending_proposals': TimeProposal.query.filter_by(status='pending').count(),
        'upcoming_sessions': TrainingSession.query.filter(
            TrainingSession.start_time > datetime.utcnow(),
            TrainingSession.status == 'scheduled'
        ).count()
    }
    
    # Sessions à venir
    upcoming_sessions = TrainingSession.query.filter(
        TrainingSession.start_time > datetime.utcnow(),
        TrainingSession.status == 'scheduled'
    ).order_by(TrainingSession.start_time).limit(5).all()
    
    # Propositions en attente
    pending_proposals = TimeProposal.query.filter_by(
        status='pending'
    ).order_by(TimeProposal.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        upcoming_sessions=upcoming_sessions,
        pending_proposals=pending_proposals
    )


@admin.route('/services')
@login_required
def manage_services():
    """Gestion des services."""
    services = Service.query.all()
    return render_template('admin/services.html', services=services)


@admin.route('/service/<service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    """Édition d'un service."""
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        service.name = request.form.get('name')
        service.manager_name = request.form.get('manager_name')
        service.manager_email = request.form.get('manager_email')
        service.color = request.form.get('color')
        
        db.session.commit()
        flash('Service mis à jour avec succès.', 'success')
        return redirect(url_for('admin.manage_services'))
    
    return render_template('admin/edit_service.html', service=service)


@admin.route('/trainings')
@login_required
def manage_trainings():
    """Gestion des formations."""
    trainings = Training.query.all()
    services = Service.query.all()
    return render_template('admin/trainings.html', trainings=trainings, services=services)


@admin.route('/training/add', methods=['POST'])
@login_required
def add_training():
    """Ajouter une nouvelle formation."""
    if request.method == 'POST':
        name = request.form.get('name')
        service_id = request.form.get('service_id')
        duration = int(request.form.get('duration', 90))
        description = request.form.get('description')
        custom_id = request.form.get('id')
        
        # Validation
        if not name or not service_id:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return redirect(url_for('admin.manage_trainings'))
        
        # Vérifier si le service existe
        service = Service.query.get(service_id)
        if not service:
            flash('Service introuvable.', 'danger')
            return redirect(url_for('admin.manage_trainings'))
        
        # Générer un ID si non spécifié
        if not custom_id:
            # Créer un ID basé sur le service et un nom simplifié
            from slugify import slugify
            custom_id = f"{service_id}-{slugify(name)}"
        
        # Vérifier si l'ID existe déjà
        existing_training = Training.query.filter_by(id=custom_id).first()
        if existing_training:
            flash(f'Une formation avec l\'ID "{custom_id}" existe déjà.', 'danger')
            return redirect(url_for('admin.manage_trainings'))
        
        # Créer la formation
        training = Training(
            id=custom_id,
            service_id=service_id,
            name=name,
            description=description,
            duration=duration
        )
        
        try:
            db.session.add(training)
            db.session.commit()
            flash('Formation ajoutée avec succès.', 'success')
            
            # Log l'action
            log_audit_event(
                'create',
                'training',
                training.id,
                f"Formation '{name}' créée pour le service '{service.name}'"
            )
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout de la formation: {str(e)}', 'danger')
        
    return redirect(url_for('admin.manage_trainings'))


@admin.route('/training/<training_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_training(training_id):
    """Édition d'une formation."""
    training = Training.query.get_or_404(training_id)
    services = Service.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        service_id = request.form.get('service_id')
        duration = int(request.form.get('duration', 90))
        description = request.form.get('description')
        
        # Validation
        if not name or not service_id:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('admin/edit_training.html', training=training, services=services)
        
        # Vérifier si le service existe
        service = Service.query.get(service_id)
        if not service:
            flash('Service introuvable.', 'danger')
            return render_template('admin/edit_training.html', training=training, services=services)
        
        # Enregistrer les modifications
        training.name = name
        training.service_id = service_id
        training.duration = duration
        training.description = description
        
        try:
            db.session.commit()
            flash('Formation mise à jour avec succès.', 'success')
            
            # Log l'action
            log_audit_event(
                'update',
                'training',
                training.id,
                f"Formation '{name}' mise à jour"
            )
            
            return redirect(url_for('admin.manage_trainings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour de la formation: {str(e)}', 'danger')
    
    return render_template('admin/edit_training.html', training=training, services=services)


@admin.route('/training/<training_id>/delete', methods=['POST'])
@login_required
def delete_training(training_id):
    """Supprimer une formation."""
    training = Training.query.get_or_404(training_id)
    
    try:
        # Récupérer les informations pour le log
        training_name = training.name
        service_name = training.service.name
        
        # Supprimer d'abord les entités dépendantes
        # 1. Supprimer les documents
        Document.query.filter_by(training_id=training_id).delete()
        
        # 2. Supprimer les propositions
        TimeProposal.query.filter_by(training_id=training_id).delete()
        
        # 3. Supprimer les sessions (et leurs présences)
        sessions = TrainingSession.query.filter_by(training_id=training_id).all()
        for session in sessions:
            Attendance.query.filter_by(session_id=session.id).delete()
            db.session.delete(session)
        
        # 4. Supprimer la formation
        db.session.delete(training)
        db.session.commit()
        
        flash('Formation supprimée avec succès.', 'success')
        
        # Log l'action
        log_audit_event(
            'delete',
            'training',
            training_id,
            f"Formation '{training_name}' supprimée du service '{service_name}'"
        )
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression de la formation: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_trainings'))


@admin.route('/groups')
@login_required
def manage_groups():
    """Gestion des groupes."""
    groups = Group.query.all()
    return render_template('admin/groups.html', groups=groups)


@admin.route('/group/<group_id>', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    """Édition d'un groupe."""
    group = Group.query.get_or_404(group_id)
    
    if request.method == 'POST':
        group.name = request.form.get('name')
        group.min_participants = int(request.form.get('min_participants'))
        group.max_participants = int(request.form.get('max_participants'))
        group.status = request.form.get('status')
        
        db.session.commit()
        flash('Groupe mis à jour avec succès.', 'success')
        return redirect(url_for('admin.manage_groups'))
    
    return render_template('admin/edit_group.html', group=group)


@admin.route('/group/<group_id>/participants')
@login_required
def group_participants(group_id):
    """Participants d'un groupe."""
    group = Group.query.get_or_404(group_id)
    participants = Participant.query.filter_by(group_id=group_id).all()
    
    return render_template('admin/group_participants.html', group=group, participants=participants)


@admin.route('/sessions')
@login_required
def manage_sessions():
    """Gestion des sessions."""
    # Filtrage par formation si spécifié
    training_id = request.args.get('training_id')
    
    if training_id:
        sessions = TrainingSession.query.filter_by(training_id=training_id).order_by(TrainingSession.start_time.desc()).all()
        training = Training.query.get_or_404(training_id)
        return render_template('admin/sessions.html', sessions=sessions, training=training)
    else:
        sessions = TrainingSession.query.order_by(TrainingSession.start_time.desc()).all()
        return render_template('admin/sessions.html', sessions=sessions)


@admin.route('/session/<session_id>', methods=['GET', 'POST'])
@login_required
def edit_session(session_id):
    """Édition d'une session."""
    session = TrainingSession.query.get_or_404(session_id)
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        location = request.form.get('location')
        status = request.form.get('status')
        notes = request.form.get('notes')
        
        try:
            # Convertir la date et l'heure en datetime
            date_parts = date_str.split('/')
            date = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            
            start_time_parts = start_time_str.split(':')
            start_time = date.replace(hour=int(start_time_parts[0]), minute=int(start_time_parts[1]))
            
            end_time_parts = end_time_str.split(':')
            end_time = date.replace(hour=int(end_time_parts[0]), minute=int(end_time_parts[1]))
            
            # Mettre à jour la session
            session.start_time = start_time
            session.end_time = end_time
            session.location = location
            session.status = status
            session.notes = notes
            
            db.session.commit()
            flash('Session mise à jour avec succès.', 'success')
            return redirect(url_for('admin.manage_sessions'))
        except Exception as e:
            flash(f'Format de date ou heure invalide: {str(e)}', 'danger')
    
    return render_template('admin/edit_session.html', session=session)


@admin.route('/session/<session_id>/attendances')
@login_required
def session_attendances(session_id):
    """Présences d'une session."""
    session = TrainingSession.query.get_or_404(session_id)
    attendances = Attendance.query.filter_by(session_id=session_id).all()
    
    return render_template('admin/session_attendances.html', session=session, attendances=attendances)


@admin.route('/session/<session_id>/attendance/<attendance_id>', methods=['POST'])
@login_required
def update_attendance(session_id, attendance_id):
    """Mise à jour d'une présence."""
    attendance = Attendance.query.get_or_404(attendance_id)
    status = request.form.get('status')
    
    if status in ['registered', 'attended', 'absent']:
        attendance.status = status
        db.session.commit()
        flash('Présence mise à jour avec succès.', 'success')
    else:
        flash('Statut de présence invalide.', 'danger')
    
    return redirect(url_for('admin.session_attendances', session_id=session_id))


@admin.route('/proposals')
@login_required
def manage_proposals():
    """Gestion des propositions."""
    # Filtrage par formation si spécifié
    training_id = request.args.get('training_id')
    
    if training_id:
        proposals = TimeProposal.query.filter_by(training_id=training_id).order_by(TimeProposal.created_at.desc()).all()
        training = Training.query.get_or_404(training_id)
        return render_template('admin/proposals.html', proposals=proposals, training=training)
    else:
        proposals = TimeProposal.query.order_by(TimeProposal.created_at.desc()).all()
        return render_template('admin/proposals.html', proposals=proposals)


@admin.route('/proposal/<proposal_id>/approve', methods=['POST'])
@login_required
def approve_proposal(proposal_id):
    """Approuver une proposition."""
    location = request.form.get('location')
    session_id = request.form.get('session_id')
    
    if session_id and session_id.strip():
        success, result = approve_time_proposal(proposal_id, session_id, location)
    else:
        success, result = approve_time_proposal(proposal_id, None, location)
    
    if success:
        flash('Proposition approuvée avec succès.', 'success')
    else:
        flash(f'Erreur lors de l\'approbation: {result}', 'danger')
    
    return redirect(url_for('admin.manage_proposals'))


@admin.route('/proposal/<proposal_id>/reject', methods=['POST'])
@login_required
def reject_proposal(proposal_id):
    """Rejeter une proposition."""
    reason = request.form.get('reason')
    
    success, result = reject_time_proposal(proposal_id, reason)
    
    if success:
        flash('Proposition rejetée avec succès.', 'success')
    else:
        flash(f'Erreur lors du rejet: {result}', 'danger')
    
    return redirect(url_for('admin.manage_proposals'))


@admin.route('/documents')
@login_required
def manage_documents():
    """Gestion des documents."""
    # Filtrage par formation si spécifié
    training_id = request.args.get('training_id')
    
    if training_id:
        documents = Document.query.filter_by(training_id=training_id).all()
        training = Training.query.get_or_404(training_id)
        return render_template('admin/documents.html', documents=documents, training=training)
    else:
        documents = Document.query.all()
        return render_template('admin/documents.html', documents=documents)


@admin.route('/document/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    """Téléchargement d'un document."""
    trainings = Training.query.all()
    
    # Pré-sélectionner une formation si spécifiée dans l'URL
    preselect_training_id = request.args.get('training_id')
    
    if request.method == 'POST':
        training_id = request.form.get('training_id')
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = 'is_public' in request.form
        file = request.files.get('file')
        
        if not file:
            flash('Aucun fichier sélectionné.', 'danger')
            return render_template('admin/upload_document.html', trainings=trainings, preselect_training_id=training_id)
        
        success, result = save_document(training_id, file, name, description, is_public)
        
        if success:
            flash('Document téléchargé avec succès.', 'success')
            return redirect(url_for('admin.manage_documents'))
        else:
            flash(f'Erreur lors du téléchargement: {result}', 'danger')
    
    return render_template('admin/upload_document.html', trainings=trainings, preselect_training_id=preselect_training_id)


@admin.route('/document/<document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Suppression d'un document."""
    document = Document.query.get_or_404(document_id)
    
    try:
        # Supprimer le fichier
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Supprimer l'enregistrement
        db.session.delete(document)
        db.session.commit()
        
        flash('Document supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_documents'))


@admin.route('/analytics')
@login_required
def analytics():
    """Analytiques."""
    # Statistiques générales
    stats = {
        'total_participants': Participant.query.count(),
        'total_sessions': TrainingSession.query.count(),
        'total_trainings': Training.query.count(),
        'total_documents': Document.query.count(),
        'total_downloads': DocumentDownload.query.count()
    }
    
    # Statistiques par service
    services = Service.query.all()
    service_stats = []
    for service in services:
        service_stats.append({
            'service': service,
            'participants': Participant.query.join(Group).filter(Group.service_id == service.id).count(),
            'sessions': TrainingSession.query.join(Training).filter(Training.service_id == service.id).count()
        })
    
    # Statistiques par formation
    trainings = Training.query.all()
    training_stats = []
    for training in trainings:
        training_stats.append({
            'training': training,
            'sessions': TrainingSession.query.filter_by(training_id=training.id).count(),
            'proposals': TimeProposal.query.filter_by(training_id=training.id).count(),
            'documents': Document.query.filter_by(training_id=training.id).count()
        })
    
    # Préparation des données pour les graphiques
    # Sessions par service
    services_data = {
        'labels': [service.name for service in services],
        'values': [stats['sessions'] for stats in service_stats],
        'colors': [service.color for service in services]
    }
    
    # Participants par mois
    current_year = datetime.utcnow().year
    participants_by_month = []
    months = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    
    for month in range(1, 13):
        count = Participant.query.filter(
            func.extract('year', Participant.created_at) == current_year,
            func.extract('month', Participant.created_at) == month
        ).count()
        participants_by_month.append(count)
    
    participants_data = {
        'labels': months,
        'values': participants_by_month
    }
    
    # Propositions par statut
    proposals_data = {
        'pending': TimeProposal.query.filter_by(status='pending').count(),
        'approved': TimeProposal.query.filter_by(status='approved').count(),
        'rejected': TimeProposal.query.filter_by(status='rejected').count()
    }
    
    return render_template(
        'admin/analytics.html',
        stats=stats,
        service_stats=service_stats,
        training_stats=training_stats,
        services_data=services_data,
        participants_data=participants_data,
        proposals_data=proposals_data
    )


@admin.route('/export/participants')
@login_required
def export_participants():
    """Export des participants au format CSV."""
    from utils import export_participants as export_func
    
    data, filename = export_func()
    
    response = current_app.response_class(
        data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )
    
    return response


@admin.route('/export/sessions')
@login_required
def export_sessions():
    """Export des sessions au format CSV."""
    from utils import export_sessions as export_func
    
    data, filename = export_func()
    
    response = current_app.response_class(
        data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )
    
    return response


@admin.route('/send-summary')
@login_required
def send_summary():
    """Envoi manuel du résumé hebdomadaire."""
    if send_weekly_summary_to_admin():
        flash('Résumé hebdomadaire envoyé avec succès.', 'success')
    else:
        flash('Erreur lors de l\'envoi du résumé hebdomadaire.', 'danger')
    
    return redirect(url_for('admin.dashboard'))


# Routes API
@api.route('/sessions')
def get_sessions():
    """API pour récupérer les sessions pour le calendrier."""
    # Récupérer la date de début et de fin pour le calendrier
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    # Filtres optionnels
    service_id = request.args.get('service_id')
    status = request.args.get('status')
    
    # Convertir les dates
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.utcnow()
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = start_date + timedelta(days=30)
    
    # Construire la requête de base
    query = TrainingSession.query.join(Training).join(Service)
    
    # Appliquer les filtres
    query = query.filter(
        TrainingSession.start_time >= start_date,
        TrainingSession.start_time <= end_date
    )
    
    if service_id:
        query = query.filter(Service.id == service_id)
    
    if status:
        query = query.filter(TrainingSession.status == status)
    
    # Exécuter la requête
    sessions = query.all()
    
    # Formater les résultats pour le calendrier
    events = []
    for session in sessions:
        events.append({
            'id': session.id,
            'title': session.training.name,
            'start': session.start_time.isoformat(),
            'end': session.end_time.isoformat(),
            'color': session.training.service.color,
            'url': url_for('admin.edit_session', session_id=session.id) if 'admin_logged_in' in flask.session else url_for('main.training_details', training_id=session.training_id),
            'description': session.training.description,
            'location': session.location,
            'status': session.status,
            'training_id': session.training_id,
            'service_id': session.training.service_id,
            'service_name': session.training.service.name
        })
    
    return jsonify(events)


@api.route('/check-conflict', methods=['POST'])
def check_conflict():
    """API pour vérifier les conflits d'horaires."""
    data = request.json
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    
    # Convertir les dates
    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.fromisoformat(end_time_str)
    
    # Vérifier les conflits
    conflicts = TrainingSession.query.filter(
        TrainingSession.start_time < end_time,
        TrainingSession.end_time > start_time
    ).all()
    
    # Formater les résultats
    result = {
        'conflict': len(conflicts) > 0,
        'sessions': []
    }
    
    for session in conflicts:
        result['sessions'].append({
            'id': session.id,
            'title': session.training.name,
            'start': session.start_time.isoformat(),
            'end': session.end_time.isoformat()
        })
    
    return jsonify(result)


@api.route('/proposal/<proposal_id>/status')
def get_proposal_status(proposal_id):
    """API pour récupérer le statut d'une proposition."""
    proposal = TimeProposal.query.get_or_404(proposal_id)
    
    status_labels = {
        'pending': 'En attente',
        'approved': 'Approuvée',
        'rejected': 'Rejetée'
    }
    
    return jsonify({
        'id': proposal.id,
        'status': proposal.status,
        'statusLabel': status_labels.get(proposal.status, proposal.status),
        'updated_at': proposal.updated_at.isoformat()
    })


# Enregistrement des blueprints
def register_blueprints(app):
    """Enregistre les blueprints dans l'application."""
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)

FICHIER: services.py
"""
Services pour le système de réservation Anecoop.
Ce module contient les services métier qui encapsulent la logique de l'application.
"""

import os
import secrets
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, current_app, request
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from models import (
    db, Service, Training, Group, Participant, Session, 
    Attendance, TimeProposal, Document, DocumentDownload, AuditLog
)

# Initialisation des services
mail = Mail()
logger = logging.getLogger(__name__)

# Services d'authentification
def login_required(f):
    """Décorateur pour vérifier qu'un utilisateur est connecté."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def authenticate_admin(password):
    """Authentifie un administrateur."""
    admin_password = current_app.config['ADMIN_PASSWORD']
    if password == admin_password:
        session['admin_logged_in'] = True
        session['login_time'] = datetime.utcnow().isoformat()
        session.permanent = True
        log_audit_event('login', 'admin', 'admin', 'Connexion administrateur')
        return True
    return False


def logout_admin():
    """Déconnecte un administrateur."""
    if 'admin_logged_in' in session:
        log_audit_event('logout', 'admin', 'admin', 'Déconnexion administrateur')
        session.pop('admin_logged_in', None)
        session.pop('login_time', None)


# Service d'initialisation de la base de données
def initialize_database():
    """Initialise la base de données avec les données de base si elle est vide."""
    # Créer les tables si elles n'existent pas
    db.create_all()
    
    # Vérifier si les services existent déjà
    if Service.query.count() == 0:
        # Ajouter les services depuis la configuration
        for service_id, service_data in current_app.config['SERVICES'].items():
            service = Service(
                id=service_id,
                name=service_data['name'],
                manager_name=service_data['manager'],
                manager_email=service_data['email'],
                color=service_data['color']
            )
            db.session.add(service)
        
        db.session.commit()
        logger.info("Services initialisés avec succès")
    
    # Vérifier si les formations existent déjà
    if Training.query.count() == 0:
        # Récupérer tous les services
        services = Service.query.all()
        if services:
            # Ajouter les formations à chaque service
            for training_data in current_app.config['TRAININGS']:
                # Répartir les formations entre les services
                for service in services:
                    training = Training(
                        id=f"{service.id}-{training_data['id']}",
                        service_id=service.id,
                        name=training_data['name'],
                        description=training_data['description'],
                        duration=training_data['duration']
                    )
                    db.session.add(training)
            
            db.session.commit()
            logger.info("Formations initialisées avec succès")
    
    # Créer le dossier d'uploads s'il n'existe pas
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        logger.info(f"Dossier d'uploads créé: {upload_folder}")


def send_email(subject, recipients, template, **kwargs):
    """Envoie un email avec le template spécifié."""
    try:
        # Vérification des paramètres SMTP
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        if not all([mail_server, mail_port, mail_username, mail_password, mail_sender]):
            logger.error("Configuration email incomplète")
            return False
        
        # Préparation du message
        msg = MIMEMultipart()
        msg['From'] = mail_sender
        msg['Subject'] = subject
        
        # Si un seul destinataire, le mettre dans un tableau
        if isinstance(recipients, str):
            recipients = [recipients]
        
        msg['To'] = ", ".join(recipients)
        
        # Formatage du template avec les paramètres
        html_content = template.format(**kwargs)
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connexion au serveur SMTP et envoi
        try:
            logger.info(f"Tentative de connexion au serveur SMTP {mail_server}:{mail_port}")
            
            # Connexion directe au serveur SMTP avec logging des étapes
            server = smtplib.SMTP(mail_server, mail_port)
            server.set_debuglevel(1)  # Debug mode pour voir les échanges
            
            # Démarrer la négociation TLS si nécessaire
            if current_app.config.get('MAIL_USE_TLS'):
                logger.info("Activation du mode TLS")
                server.starttls()
            
            # Connexion avec les identifiants
            logger.info(f"Tentative d'authentification avec l'utilisateur {mail_username}")
            server.login(mail_username, mail_password)
            
            # Envoi du message
            logger.info(f"Envoi du message à {recipients}")
            server.sendmail(mail_sender, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email envoyé avec succès à {recipients}")
            return True
            
        except smtplib.SMTPException as smtp_error:
            logger.error(f"Erreur SMTP lors de l'envoi d'email: {str(smtp_error)}")
            
            # En cas d'erreur d'authentification, essayer avec une autre méthode
            if "Authentication failed" in str(smtp_error):
                logger.info("Tentative avec une méthode d'authentification alternative")
                try:
                    server = smtplib.SMTP(mail_server, mail_port)
                    server.ehlo()
                    if current_app.config.get('MAIL_USE_TLS'):
                        server.starttls()
                    server.ehlo()
                    server.login(mail_username, mail_password)
                    server.sendmail(mail_sender, recipients, msg.as_string())
                    server.close()
                    logger.info("Email envoyé avec la méthode alternative")
                    return True
                except Exception as alt_error:
                    logger.error(f"Échec de la méthode alternative: {str(alt_error)}")
            
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email: {str(e)}")
        return False


def send_confirmation_email(email, name, training_name, proposed_time, token):
    """Envoie un email de confirmation pour une proposition de créneau."""
    subject = f"Confirmation de proposition - {training_name}"
    template = """
    <html>
    <body>
        <h2>Confirmation de proposition de créneau</h2>
        <p>Bonjour {name},</p>
        <p>Nous avons bien reçu votre proposition de créneau pour la formation <strong>{training_name}</strong> le {date} à {time}.</p>
        <p>Votre proposition est en cours d'examen. Vous recevrez une notification une fois qu'elle sera traitée.</p>
        <p>Pour suivre l'état de votre proposition, utilisez ce lien: <a href="{tracking_link}">Suivre ma proposition</a></p>
        <p>Merci pour votre intérêt pour nos formations!</p>
        <p>L'équipe Anecoop</p>
    </body>
    </html>
    """
    date_str = proposed_time.strftime("%d/%m/%Y")
    time_str = proposed_time.strftime("%H:%M")
    
    # Correction de l'URL - ajout du préfixe 'main'
    tracking_link = url_for('main.track_proposal', token=token, _external=True)
    
    
    return send_email(
        subject=subject,
        recipients=[email],
        template=template,
        name=name,
        training_name=training_name,
        date=date_str,
        time=time_str,
        tracking_link=tracking_link
    )


def send_approval_email(proposal):
    """Envoie un email d'approbation pour une proposition de créneau."""
    subject = f"Proposition acceptée - {proposal.training.name}"
    template = """
    <html>
    <body>
        <h2>Proposition de créneau acceptée</h2>
        <p>Bonjour {name},</p>
        <p>Nous avons le plaisir de vous informer que votre proposition de créneau pour la formation <strong>{training_name}</strong> a été acceptée.</p>
        <p>La formation aura lieu le {date} à {time} à {location}.</p>
        <p>Vous recevrez un rappel quelques jours avant la formation.</p>
        <p>Pour plus d'informations ou pour télécharger des documents préparatoires, consultez la page de la formation: <a href="{training_link}">Accéder à la formation</a></p>
        <p>Merci et à bientôt!</p>
        <p>L'équipe Anecoop</p>
    </body>
    </html>
    """
    date_str = proposal.proposed_time.strftime("%d/%m/%Y")
    time_str = proposal.proposed_time.strftime("%H:%M")
    location = proposal.session.location if proposal.session else "À déterminer"
    training_link = url_for('training_details', training_id=proposal.training_id, _external=True)
    
    return send_email(
        subject=subject,
        recipients=[proposal.proposer_email],
        template=template,
        name=proposal.proposer_name,
        training_name=proposal.training.name,
        date=date_str,
        time=time_str,
        location=location,
        training_link=training_link
    )


def send_rejection_email(proposal):
    """Envoie un email de rejet pour une proposition de créneau."""
    subject = f"Proposition non retenue - {proposal.training.name}"
    template = """
    <html>
    <body>
        <h2>Proposition de créneau non retenue</h2>
        <p>Bonjour {name},</p>
        <p>Nous vous remercions pour votre proposition de créneau pour la formation <strong>{training_name}</strong>.</p>
        <p>Malheureusement, nous n'avons pas pu retenir votre proposition pour la date du {date} à {time}.</p>
        <p>Nous vous invitons à proposer d'autres créneaux qui vous conviendraient en cliquant sur ce lien: <a href="{new_proposal_link}">Faire une nouvelle proposition</a></p>
        <p>Vous pouvez également consulter les sessions déjà planifiées: <a href="{sessions_link}">Voir les sessions planifiées</a></p>
        <p>Merci pour votre compréhension!</p>
        <p>L'équipe Anecoop</p>
    </body>
    </html>
    """
    date_str = proposal.proposed_time.strftime("%d/%m/%Y")
    time_str = proposal.proposed_time.strftime("%H:%M")
    new_proposal_link = url_for('propose_time', training_id=proposal.training_id, _external=True)
    sessions_link = url_for('training_sessions', training_id=proposal.training_id, _external=True)
    
    return send_email(
        subject=subject,
        recipients=[proposal.proposer_email],
        template=template,
        name=proposal.proposer_name,
        training_name=proposal.training.name,
        date=date_str,
        time=time_str,
        new_proposal_link=new_proposal_link,
        sessions_link=sessions_link
    )


def send_reminder_email(session, participant):
    """Envoie un email de rappel pour une session à venir."""
    subject = f"Rappel - Formation {session.training.name}"
    template = """
    <html>
    <body>
        <h2>Rappel de formation à venir</h2>
        <p>Bonjour {name},</p>
        <p>Nous vous rappelons que vous êtes inscrit(e) à la formation <strong>{training_name}</strong> qui aura lieu bientôt.</p>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Heure:</strong> {time}</p>
        <p><strong>Lieu:</strong> {location}</p>
        <p>Si vous avez des questions ou si vous ne pouvez pas participer, veuillez nous contacter rapidement.</p>
        <p>À bientôt!</p>
        <p>L'équipe Anecoop</p>
    </body>
    </html>
    """
    date_str = session.start_time.strftime("%d/%m/%Y")
    time_str = session.start_time.strftime("%H:%M")
    
    return send_email(
        subject=subject,
        recipients=[participant.email],
        template=template,
        name=participant.name,
        training_name=session.training.name,
        date=date_str,
        time=time_str,
        location=session.location or "À déterminer"
    )


def send_weekly_summary_to_admin():
    """Envoie un résumé hebdomadaire à l'administrateur."""
    # Récupérer l'administrateur (ici, on utilise l'email par défaut)
    admin_email = current_app.config['MAIL_DEFAULT_SENDER']
    
    # Récupérer les statistiques de la semaine
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    new_proposals = TimeProposal.query.filter(
        TimeProposal.created_at >= week_ago
    ).count()
    
    upcoming_sessions = Session.query.filter(
        Session.start_time >= now,
        Session.start_time <= now + timedelta(days=7),
        Session.status == 'scheduled'
    ).count()
    
    completed_sessions = Session.query.filter(
        Session.status == 'completed',
        Session.end_time >= week_ago,
        Session.end_time <= now
    ).count()
    
    new_participants = Participant.query.filter(
        Participant.created_at >= week_ago
    ).count()
    
    subject = f"Résumé hebdomadaire - Système de réservation Anecoop"
    template = """
    <html>
    <body>
        <h2>Résumé hebdomadaire - Système de réservation Anecoop</h2>
        <p>Voici le résumé des activités de la semaine du {start_date} au {end_date}:</p>
        
        <h3>Statistiques générales</h3>
        <ul>
            <li>Nouvelles propositions de créneaux: {new_proposals}</li>
            <li>Sessions à venir cette semaine: {upcoming_sessions}</li>
            <li>Sessions terminées cette semaine: {completed_sessions}</li>
            <li>Nouveaux participants: {new_participants}</li>
        </ul>
        
        <h3>Propositions en attente</h3>
        <p>Il y a actuellement {pending_proposals} propositions en attente de validation.</p>
        
        <h3>Actions recommandées</h3>
        <ul>
            <li><a href="{pending_link}">Traiter les propositions en attente</a></li>
            <li><a href="{upcoming_link}">Vérifier les sessions à venir</a></li>
            <li><a href="{dashboard_link}">Accéder au tableau de bord</a></li>
        </ul>
        
        <p>Ce message est généré automatiquement par le système de réservation Anecoop.</p>
    </body>
    </html>
    """
    
    # Calculer le nombre de propositions en attente
    pending_proposals = TimeProposal.query.filter_by(status='pending').count()
    
    # Créer les liens pour le dashboard
    pending_link = url_for('admin_pending_proposals', _external=True)
    upcoming_link = url_for('admin_upcoming_sessions', _external=True)
    dashboard_link = url_for('admin_dashboard', _external=True)
    
    return send_email(
        subject=subject,
        recipients=[admin_email],
        template=template,
        start_date=week_ago.strftime("%d/%m/%Y"),
        end_date=now.strftime("%d/%m/%Y"),
        new_proposals=new_proposals,
        upcoming_sessions=upcoming_sessions,
        completed_sessions=completed_sessions,
        new_participants=new_participants,
        pending_proposals=pending_proposals,
        pending_link=pending_link,
        upcoming_link=upcoming_link,
        dashboard_link=dashboard_link
    )


def create_time_proposal(training_id, email, name, department, proposed_time):
    """Crée une nouvelle proposition de créneau."""
    try:
        # Vérifier si la formation existe
        training = Training.query.get(training_id)
        if not training:
            return False, "Formation introuvable"
        
        # Créer un token unique pour le suivi
        token = secrets.token_urlsafe(16)
        
        # Créer la proposition
        proposal = TimeProposal(
            training_id=training_id,
            proposer_email=email,
            proposer_name=name,
            department=department,
            proposed_time=proposed_time,
            status='pending',
            notes=f"Token de suivi: {token}"
        )
        
        db.session.add(proposal)
        db.session.commit()
        
        # Envoyer l'email de confirmation
        try:
            send_confirmation_email(email, name, training.name, proposed_time, token)
            logger.info(f"Email de confirmation envoyé à {email}")
        except Exception as email_error:
            logger.error(f"Erreur lors de l'envoi de l'email: {str(email_error)}")
            # Ne pas échouer complètement si uniquement l'email ne fonctionne pas
        
        # Enregistrer l'événement dans les logs
        log_audit_event(
            'create',
            'time_proposal',
            proposal.id,
            f"Nouvelle proposition pour {training.name} par {name}"
        )
        
        return True, proposal.id
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création d'une proposition de créneau: {str(e)}")
        return False, str(e)

def approve_time_proposal(proposal_id, session_id=None, location=None):
    """Approuve une proposition de créneau et crée une session."""
    try:
        # Récupérer la proposition
        proposal = TimeProposal.query.get(proposal_id)
        if not proposal:
            return False, "Proposition introuvable"
        
        # Vérifier si une session existante est fournie
        if session_id:
            session = Session.query.get(session_id)
            if not session:
                return False, "Session introuvable"
        else:
            # Créer une nouvelle session
            training = Training.query.get(proposal.training_id)
            if not training:
                return False, "Formation introuvable"
            
            # Calculer l'heure de fin
            end_time = proposal.proposed_time + timedelta(minutes=training.duration)
            
            # Créer un nouveau groupe si nécessaire
            group = Group.query.filter_by(
                service_id=training.service_id,
                status='active'
            ).order_by(Group.created_at.desc()).first()
            
            if not group or Group.query.join(Session).filter(
                Group.id == group.id,
                Session.status.in_(['scheduled', 'completed'])
            ).count() >= 4:  # Max 4 sessions par groupe
                # Créer un nouveau groupe
                group_name = f"Groupe {training.service.name} - {datetime.utcnow().strftime('%B %Y')}"
                group = Group(
                    service_id=training.service_id,
                    name=group_name,
                    status='active'
                )
                db.session.add(group)
                db.session.flush()  # Obtenir l'ID sans commit
            
            # Créer la session
            session = Session(
                training_id=training.id,
                group_id=group.id,
                start_time=proposal.proposed_time,
                end_time=end_time,
                location=location or "À déterminer",
                status='scheduled'
            )
            db.session.add(session)
        
        # Mettre à jour la proposition
        proposal.status = 'approved'
        proposal.session_id = session.id
        db.session.commit()
        
        # Créer un participant pour le proposeur
        participant = Participant.query.filter_by(
            email=proposal.proposer_email,
            group_id=session.group_id
        ).first()
        
        if not participant:
            participant = Participant(
                group_id=session.group_id,
                email=proposal.proposer_email,
                name=proposal.proposer_name,
                department=proposal.department,
                verified=True
            )
            db.session.add(participant)
            db.session.commit()
        
        # Créer une présence pour le participant
        attendance = Attendance(
            session_id=session.id,
            participant_id=participant.id,
            status='registered'
        )
        db.session.add(attendance)
        db.session.commit()
        
        # Envoyer l'email d'approbation
        send_approval_email(proposal)
        
        # Enregistrer l'événement dans les logs
        log_audit_event(
            'approve',
            'time_proposal',
            proposal.id,
            f"Proposition approuvée pour {proposal.training.name} par {proposal.proposer_name}"
        )
        
        return True, session.id
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'approbation d'une proposition: {str(e)}")
        return False, str(e)


def reject_time_proposal(proposal_id, reason=None):
    """Rejette une proposition de créneau."""
    try:
        # Récupérer la proposition
        proposal = TimeProposal.query.get(proposal_id)
        if not proposal:
            return False, "Proposition introuvable"
        
        # Mettre à jour la proposition
        proposal.status = 'rejected'
        if reason:
            proposal.notes = (proposal.notes or "") + f"\nMotif de rejet: {reason}"
        
        db.session.commit()
        
        # Envoyer l'email de rejet
        send_rejection_email(proposal)
        
        # Enregistrer l'événement dans les logs
        log_audit_event(
            'reject',
            'time_proposal',
            proposal.id,
            f"Proposition rejetée pour {proposal.training.name} par {proposal.proposer_name}"
        )
        
        return True, proposal.id
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors du rejet d'une proposition: {str(e)}")
        return False, str(e)


# Service de gestion des documents
def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_document(training_id, file, name=None, description=None, is_public=True):
    """Enregistre un document téléchargé."""
    try:
        if file and allowed_file(file.filename):
            # Sécuriser le nom du fichier
            filename = secure_filename(file.filename)
            
            # Générer un nom unique pour éviter les collisions
            unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{filename}"
            
            # Définir le chemin complet
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Enregistrer le fichier
            file.save(file_path)
            
            # Créer l'enregistrement dans la base de données
            document = Document(
                training_id=training_id,
                name=name or filename,
                file_path=unique_filename,
                file_type=filename.rsplit('.', 1)[1].lower(),
                file_size=os.path.getsize(file_path),
                description=description,
                is_public=is_public
            )
            
            db.session.add(document)
            db.session.commit()
            
            # Enregistrer l'événement dans les logs
            log_audit_event(
                'upload',
                'document',
                document.id,
                f"Document téléchargé pour la formation {training_id}: {name or filename}"
            )
            
            return True, document.id
        else:
            return False, "Type de fichier non autorisé"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'enregistrement d'un document: {str(e)}")
        return False, str(e)


def log_document_download(document_id, user_email, user_name=None):
    """Enregistre le téléchargement d'un document."""
    try:
        # Créer l'enregistrement de téléchargement
        download = DocumentDownload(
            document_id=document_id,
            user_email=user_email,
            user_name=user_name,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        
        db.session.add(download)
        db.session.commit()
        
        return True, download.id
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'enregistrement d'un téléchargement: {str(e)}")
        return False, str(e)


# Service d'audit
def log_audit_event(action, entity_type, entity_id, description=None):
    """Enregistre un événement d'audit."""
    try:
        # Récupérer l'email de l'utilisateur si disponible
        user_email = None
        if 'admin_logged_in' in session and session['admin_logged_in']:
            user_email = 'admin'
        elif 'user_email' in session:
            user_email = session['user_email']
        
        # Créer l'enregistrement d'audit
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_email=user_email,
            user_ip=request.remote_addr,
            changes={'description': description} if description else None
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'enregistrement d'un événement d'audit: {str(e)}")
        return False

FICHIER: setup.py
#!/usr/bin/env python3
"""
Script d'initialisation pour le système de réservation Anecoop.
Ce script vérifie l'environnement et prépare l'application pour un premier démarrage.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Définir les dossiers et fichiers nécessaires
REQUIRED_FOLDERS = [
    "static",
    "static/css",
    "static/js",
    "static/img",
    "static/uploads",
    "templates",
    "templates/admin",
    "templates/errors"
]

# Vérifie si un fichier .env existe, sinon le crée
def check_env_file():
    if not os.path.exists('.env'):
        print("[INFO] Création du fichier .env...")
        with open('.env', 'w') as f:
            f.write("""# Configuration générale
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=anecoopFormationsBooking2025SecretKey

# Configuration base de données
DATABASE_URL=postgresql://khoiffzx:jagtqaxjqdwxkyxklzjw@alpha.europe.mkdb.sh:5432/wypdrdri

# Configuration email
MAIL_SERVER=outlook.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=kbivia@anecoop-france.com
MAIL_PASSWORD=kb3272XM&
MAIL_DEFAULT_SENDER=kbivia@anecoop-france.com

# Configuration admin
ADMIN_PASSWORD=Anecoop2025

# Configuration application
APP_NAME=Anecoop Formations
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max upload size
SESSION_LIFETIME=1440  # 24 heures en minutes
""")
        print("[OK] Fichier .env créé avec succès")
    else:
        print("[OK] Fichier .env existant")

# Créé les dossiers nécessaires
def create_required_directories():
    print("[INFO] Vérification des dossiers requis...")
    for folder in REQUIRED_FOLDERS:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[INFO] Dossier '{folder}' créé")
        else:
            print(f"[OK] Dossier '{folder}' existant")

# Vérifie les dépendances Python
def check_python_dependencies():
    try:
        # Vérifie si pip est installé
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, stdout=subprocess.PIPE)
        
        print("[INFO] Vérification des dépendances Python...")
        # Installe les dépendances depuis requirements.txt
        if os.path.exists('requirements.txt'):
            print("[INFO] Installation des dépendances depuis requirements.txt...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("[OK] Dépendances installées avec succès")
        else:
            print("[ERREUR] Fichier requirements.txt introuvable")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("[ERREUR] Erreur lors de la vérification des dépendances")
        sys.exit(1)

# Initialise la base de données
def initialize_database():
    print("[INFO] Initialisation de la base de données...")
    try:
        # Exécute l'initialisation de la base de données via Flask
        subprocess.run([sys.executable, "-c", 
                       "from app import app; from models import db; from services import initialize_database; app.app_context().push(); db.create_all(); initialize_database()"], 
                       check=True)
        print("[OK] Base de données initialisée avec succès")
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Erreur lors de l'initialisation de la base de données: {str(e)}")
        sys.exit(1)

# Vérifie les ressources statiques
def check_static_resources():
    print("[INFO] Vérification des ressources statiques...")
    
    # Vérifie si le logo existe
    logo_path = Path("static/img/logo.png")
    if not logo_path.exists():
        print("[INFO] Création d'un logo par défaut...")
        # Créer un logo simple par défaut
        try:
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
            
            # Créer une image 200x200 avec un fond blanc
            img = Image.new('RGBA', (200, 80), color=(255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Dessiner un rectangle arrondi
            draw.rounded_rectangle([(10, 10), (190, 70)], fill=(13, 110, 253, 255), radius=10)
            
            # Ajouter du texte
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except IOError:
                font = ImageFont.load_default()
            
            draw.text((35, 25), "Anecoop", fill=(255, 255, 255, 255), font=font)
            
            # Sauvegarder l'image
            logo_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(logo_path)
            print(f"[OK] Logo par défaut créé à {logo_path}")
        except ImportError:
            print("[INFO] Pillow non installé, logo par défaut non créé")
    else:
        print(f"[OK] Logo existant à {logo_path}")

    # Vérifier les fichiers CSS et JS
    if not os.path.exists("static/css/style.css"):
        print("[ATTENTION] Fichier CSS principal manquant")
    if not os.path.exists("static/js/main.js"):
        print("[ATTENTION] Fichier JavaScript principal manquant")

# Fonction principale
def main():
    print("=" * 60)
    print("INITIALISATION DU SYSTÈME DE RÉSERVATION ANECOOP")
    print("=" * 60)
    
    check_env_file()
    create_required_directories()
    check_python_dependencies()
    check_static_resources()
    initialize_database()
    
    print("\n" + "=" * 60)
    print("INITIALISATION TERMINÉE AVEC SUCCÈS")
    print("=" * 60)
    print("\nPour démarrer l'application, exécutez:")
    print("  flask run")
    print("\nPour accéder au panneau d'administration, utilisez:")
    print("  URL: http://localhost:5000/admin")
    print("  Mot de passe: Anecoop2025")
    print("=" * 60)

if __name__ == "__main__":
    main()


FICHIER: static\css\admin-dark.css
/* 
 * Anecoop Formations - Admin Dark Mode Stylesheet
 * ------------------------------
 */

/* Admin dark mode variables */
:root {
    --admin-dark-bg: #121212;
    --admin-dark-surface: #1e1e1e;
    --admin-dark-primary: #90caf9;
    --admin-dark-secondary: #b0bec5;
    --admin-dark-success: #81c784;
    --admin-dark-danger: #f48fb1;
    --admin-dark-warning: #ffe082;
    --admin-dark-info: #80deea;
    --admin-dark-text: #e0e0e0;
    --admin-dark-text-secondary: #b0b0b0;
    --admin-dark-border: rgba(255, 255, 255, 0.12);
    --admin-dark-card-bg: #2d2d2d;
    --admin-dark-input-bg: #424242;
    --admin-dark-hover: rgba(255, 255, 255, 0.08);
}

[data-bs-theme="dark"] {
    color-scheme: dark;
    
    /* General styling */
    --bs-body-color: var(--admin-dark-text);
    --bs-body-bg: var(--admin-dark-bg);
    --bs-border-color: var(--admin-dark-border);
    
    /* Components */
    --bs-primary: var(--admin-dark-primary);
    --bs-secondary: var(--admin-dark-secondary);
    --bs-success: var(--admin-dark-success);
    --bs-danger: var(--admin-dark-danger);
    --bs-warning: var(--admin-dark-warning);
    --bs-info: var(--admin-dark-info);
    
    color: var(--admin-dark-text);
    background-color: var(--admin-dark-bg);
}

/* Cards */
[data-bs-theme="dark"] .card {
    background-color: var(--admin-dark-card-bg);
    border-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .card-header,
[data-bs-theme="dark"] .card-footer {
    background-color: rgba(0, 0, 0, 0.2);
    border-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .bg-light {
    background-color: var(--admin-dark-surface) !important;
}

/* Table styling */
[data-bs-theme="dark"] .table {
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .table-striped > tbody > tr:nth-of-type(odd) > * {
    background-color: rgba(255, 255, 255, 0.05);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .table-hover > tbody > tr:hover > * {
    background-color: rgba(255, 255, 255, 0.075);
    color: var(--admin-dark-text);
}

/* DataTables styling */
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_length,
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_filter,
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_info,
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_processing,
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_paginate {
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .dataTables_wrapper .dataTables_paginate .paginate_button {
    color: var(--admin-dark-text) !important;
}

[data-bs-theme="dark"] .dataTables_wrapper .dataTables_paginate .paginate_button.current,
[data-bs-theme="dark"] .dataTables_wrapper .dataTables_paginate .paginate_button.current:hover {
    color: var(--admin-dark-bg) !important;
    background: var(--admin-dark-primary);
    border-color: var(--admin-dark-primary);
}

[data-bs-theme="dark"] .dataTables_wrapper .dataTables_paginate .paginate_button:hover {
    color: var(--admin-dark-bg) !important;
    background: var(--admin-dark-primary);
    border-color: var(--admin-dark-primary);
}

/* Form controls */
[data-bs-theme="dark"] .form-control,
[data-bs-theme="dark"] .form-select {
    background-color: var(--admin-dark-input-bg);
    border-color: var(--admin-dark-border);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .form-control:focus,
[data-bs-theme="dark"] .form-select:focus {
    background-color: var(--admin-dark-input-bg);
    border-color: var(--admin-dark-primary);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .input-group-text {
    background-color: rgba(0, 0, 0, 0.2);
    border-color: var(--admin-dark-border);
    color: var(--admin-dark-text);
}

/* List groups */
[data-bs-theme="dark"] .list-group-item {
    background-color: var(--admin-dark-card-bg);
    border-color: var(--admin-dark-border);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .list-group-item-action:hover {
    background-color: var(--admin-dark-hover);
}

/* Modal styling */
[data-bs-theme="dark"] .modal-content {
    background-color: var(--admin-dark-card-bg);
    border-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .modal-header,
[data-bs-theme="dark"] .modal-footer {
    background-color: rgba(0, 0, 0, 0.2);
    border-color: var(--admin-dark-border);
}

/* FullCalendar dark theme */
[data-bs-theme="dark"] .fc-theme-standard .fc-scrollgrid,
[data-bs-theme="dark"] .fc-theme-standard td,
[data-bs-theme="dark"] .fc-theme-standard th {
    border-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .fc-col-header-cell {
    background-color: rgba(0, 0, 0, 0.2);
}

[data-bs-theme="dark"] .fc .fc-daygrid-day-number,
[data-bs-theme="dark"] .fc .fc-col-header-cell-cushion {
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .fc-daygrid-day.fc-day-today {
    background-color: rgba(144, 202, 249, 0.2) !important;
}

[data-bs-theme="dark"] .fc-theme-standard .fc-list-day-cushion {
    background-color: var(--admin-dark-surface);
}

/* Buttons */
[data-bs-theme="dark"] .btn-outline-secondary {
    color: var(--admin-dark-secondary);
    border-color: var(--admin-dark-secondary);
}

[data-bs-theme="dark"] .btn-outline-secondary:hover {
    background-color: var(--admin-dark-secondary);
    color: var(--admin-dark-bg);
}

[data-bs-theme="dark"] .btn-light {
    background-color: var(--admin-dark-surface);
    border-color: var(--admin-dark-border);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .btn-light:hover {
    background-color: var(--admin-dark-hover);
    border-color: var(--admin-dark-border);
    color: var(--admin-dark-text);
}

/* Navbar */
[data-bs-theme="dark"] .navbar-dark {
    background-color: var(--admin-dark-surface) !important;
}

[data-bs-theme="dark"] .bg-primary {
    background-color: var(--admin-dark-surface) !important;
}

/* Dropdown menus */
[data-bs-theme="dark"] .dropdown-menu {
    background-color: var(--admin-dark-card-bg);
    border-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .dropdown-item {
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .dropdown-item:hover, 
[data-bs-theme="dark"] .dropdown-item:focus {
    background-color: var(--admin-dark-hover);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .dropdown-divider {
    border-color: var(--admin-dark-border);
}

/* Timeline */
[data-bs-theme="dark"] .timeline:before {
    background-color: var(--admin-dark-border);
}

[data-bs-theme="dark"] .timeline-marker {
    background-color: var(--admin-dark-card-bg);
    border-color: var(--admin-dark-primary);
}

[data-bs-theme="dark"] .timeline-content {
    border-color: var(--admin-dark-border);
    background-color: var(--admin-dark-card-bg);
}

[data-bs-theme="dark"] .timeline-date {
    color: var(--admin-dark-text-secondary);
}

/* Text colors */
[data-bs-theme="dark"] .text-muted {
    color: var(--admin-dark-text-secondary) !important;
}

/* Chart styling */
[data-bs-theme="dark"] .chartjs-render-monitor {
    filter: brightness(0.8) contrast(1.2);
}

/* Status badges adjustments */
[data-bs-theme="dark"] .status-pending {
    background-color: #bf9c30;
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .status-registered {
    background-color: #4cc3d9;
    color: var(--admin-dark-text);
}

/* Scroll bar styling */
[data-bs-theme="dark"] ::-webkit-scrollbar {
    width: 12px;
    height: 12px;
}

[data-bs-theme="dark"] ::-webkit-scrollbar-track {
    background: var(--admin-dark-bg);
}

[data-bs-theme="dark"] ::-webkit-scrollbar-thumb {
    background-color: #555;
    border-radius: 6px;
    border: 3px solid var(--admin-dark-bg);
}

[data-bs-theme="dark"] ::-webkit-scrollbar-thumb:hover {
    background-color: #777;
}

/* File preview */
[data-bs-theme="dark"] .file-preview {
    border-color: var(--admin-dark-border);
    background-color: var(--admin-dark-card-bg);
}

/* Custom tooltip */
[data-bs-theme="dark"] .custom-tooltip .tooltip-text {
    background-color: var(--admin-dark-surface);
    color: var(--admin-dark-text);
}

[data-bs-theme="dark"] .custom-tooltip .tooltip-text::after {
    border-color: var(--admin-dark-surface) transparent transparent transparent;
}

FICHIER: static\css\admin.css
/* 
 * Anecoop Formations - Admin Stylesheet
 * ------------------------------
 */

/* General Styles */
:root {
    --admin-primary: #0d6efd;
    --admin-secondary: #6c757d;
    --admin-success: #198754;
    --admin-danger: #dc3545;
    --admin-warning: #ffc107;
    --admin-info: #0dcaf0;
    --admin-light: #f8f9fa;
    --admin-dark: #212529;
    --admin-bg: #f8f9fa;
    --admin-sidebar-width: 280px;
    --admin-body-color: #212529;
    --admin-border-color: rgba(0, 0, 0, 0.125);
    --admin-card-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: var(--admin-bg);
    color: var(--admin-body-color);
}

/* Dashboard Cards */
.card {
    box-shadow: var(--admin-card-shadow);
    border-radius: 0.5rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.card-header h5 {
    margin-bottom: 0;
}

/* Stats Cards */
.border-primary {
    border-color: var(--admin-primary) !important;
    border-width: 2px !important;
}

.border-success {
    border-color: var(--admin-success) !important;
    border-width: 2px !important;
}

.border-info {
    border-color: var(--admin-info) !important;
    border-width: 2px !important;
}

.border-warning {
    border-color: var(--admin-warning) !important;
    border-width: 2px !important;
}

.border-danger {
    border-color: var(--admin-danger) !important;
    border-width: 2px !important;
}

.border-secondary {
    border-color: var(--admin-secondary) !important;
    border-width: 2px !important;
}

.border-dark {
    border-color: var(--admin-dark) !important;
    border-width: 2px !important;
}

.text-primary {
    color: var(--admin-primary) !important;
}

.text-success {
    color: var(--admin-success) !important;
}

.text-info {
    color: var(--admin-info) !important;
}

.text-warning {
    color: var(--admin-warning) !important;
}

.text-danger {
    color: var(--admin-danger) !important;
}

/* Data Tables */
.dataTables_wrapper {
    padding: 1rem 0;
}

.dataTables_length select {
    min-width: 60px;
}

.dataTables_filter input {
    min-width: 250px;
}

table.dataTable {
    border-collapse: collapse !important;
    margin-top: 1rem !important;
    margin-bottom: 1rem !important;
}

table.dataTable thead th {
    position: relative;
    background-image: none !important;
}

table.dataTable thead th.sorting:after,
table.dataTable thead th.sorting_asc:after,
table.dataTable thead th.sorting_desc:after {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    font-family: "Font Awesome 6 Free";
    font-weight: 900;
    opacity: 0.5;
}

table.dataTable thead th.sorting:after {
    content: "\f0dc";
}

table.dataTable thead th.sorting_asc:after {
    content: "\f0de";
    opacity: 1;
}

table.dataTable thead th.sorting_desc:after {
    content: "\f0dd";
    opacity: 1;
}

/* Forms */
.form-control:focus,
.form-select:focus {
    border-color: var(--admin-primary);
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

.form-label {
    font-weight: 500;
}

.form-text {
    font-size: 0.85rem;
}

/* Action buttons */
.action-buttons {
    white-space: nowrap;
}

.action-buttons .btn {
    margin-right: 0.25rem;
}

.btn-icon {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
}

/* Status badges */
.status-badge {
    padding: 0.25em 0.6em;
    font-size: 75%;
    font-weight: 700;
    border-radius: 0.375rem;
}

.status-scheduled {
    background-color: var(--admin-primary);
    color: white;
}

.status-completed {
    background-color: var(--admin-success);
    color: white;
}

.status-cancelled {
    background-color: var(--admin-danger);
    color: white;
}

.status-pending {
    background-color: var(--admin-warning);
    color: var(--admin-dark);
}

.status-approved {
    background-color: var(--admin-success);
    color: white;
}

.status-rejected {
    background-color: var(--admin-danger);
    color: white;
}

.status-registered {
    background-color: var(--admin-info);
    color: white;
}

.status-attended {
    background-color: var(--admin-success);
    color: white;
}

.status-absent {
    background-color: var(--admin-danger);
    color: white;
}

/* Calendar customization */
.fc-toolbar-title {
    font-size: 1.25rem !important;
    font-weight: 600;
}

.fc .fc-button-primary {
    background-color: var(--admin-primary);
    border-color: var(--admin-primary);
}

.fc .fc-button-primary:not(:disabled):active,
.fc .fc-button-primary:not(:disabled).fc-button-active {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

.fc-daygrid-day.fc-day-today {
    background-color: rgba(13, 110, 253, 0.1) !important;
}

.fc-event {
    border: none;
    padding: 2px 5px;
    font-size: 0.85rem;
}

/* Charts */
.chart-container {
    position: relative;
    margin: auto;
    height: 300px;
    width: 100%;
}

/* Modals */
.modal-header {
    background-color: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
}

.modal-footer {
    background-color: #f8f9fa;
    border-top: 1px solid #dee2e6;
}

/* Pagination */
.pagination {
    margin: 1rem 0;
}

.page-link {
    color: var(--admin-primary);
}

.page-item.active .page-link {
    background-color: var(--admin-primary);
    border-color: var(--admin-primary);
}

/* File upload previews */
.file-preview {
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
    padding: 1rem;
    margin-bottom: 1rem;
}

.file-preview-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

/* Timeline */
.timeline {
    position: relative;
    padding-left: 3rem;
}

.timeline:before {
    content: '';
    position: absolute;
    left: 0.75rem;
    top: 0;
    height: 100%;
    width: 2px;
    background-color: #dee2e6;
}

.timeline-item {
    position: relative;
    margin-bottom: 1.5rem;
}

.timeline-item:last-child {
    margin-bottom: 0;
}

.timeline-marker {
    position: absolute;
    left: -3rem;
    top: 0;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background-color: white;
    border: 2px solid var(--admin-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1;
}

.timeline-content {
    padding: 1rem;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
}

.timeline-date {
    font-size: 0.875rem;
    color: #6c757d;
}

/* Tooltips */
.custom-tooltip {
    position: relative;
    display: inline-block;
}

.custom-tooltip .tooltip-text {
    visibility: hidden;
    width: 200px;
    background-color: #212529;
    color: #fff;
    text-align: center;
    border-radius: 6px;
    padding: 5px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -100px;
    opacity: 0;
    transition: opacity 0.3s;
}

.custom-tooltip .tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #212529 transparent transparent transparent;
}

.custom-tooltip:hover .tooltip-text {
    visibility: visible;
    opacity: 1;
}

/* Animations */
.fade-in {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Responsive adjustments */
@media (max-width: 767.98px) {
    .navbar-brand {
        font-size: 1rem;
    }
    
    .chart-container {
        height: 250px;
    }
    
    .fc-toolbar-title {
        font-size: 1rem !important;
    }
    
    .timeline {
        padding-left: 2rem;
    }
    
    .timeline-marker {
        left: -2rem;
        width: 1.25rem;
        height: 1.25rem;
    }
}

FICHIER: static\css\dark-mode.css
/* 
 * Anecoop Formations - Dark Mode Stylesheet (simplifié)
 * ------------------------------
 */

/* Dark mode variables */
:root {
    --dark-bg: #121212;
    --dark-surface: #1e1e1e;
    --dark-primary: #90caf9;
    --dark-secondary: #b0bec5;
    --dark-success: #81c784;
    --dark-danger: #f48fb1;
    --dark-warning: #ffe082;
    --dark-info: #80deea;
    --dark-text: #e0e0e0;
    --dark-text-secondary: #b0b0b0;
    --dark-border: rgba(255, 255, 255, 0.12);
    --dark-card-bg: #2d2d2d;
    --dark-input-bg: #424242;
    --dark-hover: rgba(255, 255, 255, 0.08);
}

[data-bs-theme="dark"] {
    color-scheme: dark;
    
    /* General styling */
    --bs-body-color: var(--dark-text);
    --bs-body-bg: var(--dark-bg);
    --bs-border-color: var(--dark-border);
    
    /* Components */
    --bs-primary: var(--dark-primary);
    --bs-secondary: var(--dark-secondary);
    --bs-success: var(--dark-success);
    --bs-danger: var(--dark-danger);
    --bs-warning: var(--dark-warning);
    --bs-info: var(--dark-info);
    
    color: var(--dark-text);
    background-color: var(--dark-bg);
}

/* Navbar styling */
[data-bs-theme="dark"] .navbar-light {
    background-color: var(--dark-surface) !important;
}

[data-bs-theme="dark"] .navbar-light .navbar-brand,
[data-bs-theme="dark"] .navbar-light .navbar-nav .nav-link {
    color: var(--dark-text);
}

[data-bs-theme="dark"] .navbar-light .navbar-toggler-icon {
    filter: invert(1);
}

/* Card styling */
[data-bs-theme="dark"] .card {
    background-color: var(--dark-card-bg);
    border-color: var(--dark-border);
}

[data-bs-theme="dark"] .card-header,
[data-bs-theme="dark"] .card-footer {
    background-color: rgba(0, 0, 0, 0.2);
    border-color: var(--dark-border);
}

/* Background colors */
[data-bs-theme="dark"] .bg-light {
    background-color: var(--dark-surface) !important;
}

/* Footer */
[data-bs-theme="dark"] footer.bg-light {
    background-color: var(--dark-surface) !important;
    color: var(--dark-text);
}

FICHIER: static\css\style.css
/* 
 * Anecoop Formations - Main Stylesheet (simplifié)
 * ------------------------------
 */

/* General Styles */
:root {
    --primary-color: #0d6efd;
    --secondary-color: #6c757d;
    --success-color: #198754;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #0dcaf0;
    --light-color: #f8f9fa;
    --dark-color: #212529;
    --body-bg: #f8f9fa;
    --body-color: #212529;
    --border-radius: 0.375rem;
    --border-color: rgba(0, 0, 0, 0.125);
    --card-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    --hover-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    --transition-speed: 0.3s;
}

body {
    background-color: var(--body-bg);
    color: var(--body-color);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.5;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

main {
    flex: 1;
}

/* Cards */
.card {
    transition: transform var(--transition-speed), box-shadow var(--transition-speed);
    border-radius: var(--border-radius);
    overflow: hidden;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: var(--hover-shadow);
}

/* Service Cards */
.service-card {
    position: relative;
    overflow: hidden;
}

.service-card .service-color {
    height: 5px;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
}

/* Training Cards */
.training-card {
    height: 100%;
}

.training-duration {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    border-radius: 0.25rem;
    background-color: var(--light-color);
}

/* Form Styling */
.form-control:focus, .form-select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

.btn-primary {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
}

.btn-primary:hover {
    background-color: #0b5ed7;
    border-color: #0a58ca;
}

/* Animation */
.fade-in {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Status Pills */
.status-pill {
    display: inline-block;
    padding: 0.25em 0.6em;
    font-size: 75%;
    font-weight: 700;
    line-height: 1;
    text-align: center;
    white-space: nowrap;
    vertical-align: baseline;
    border-radius: 10rem;
}

.status-pending {
    background-color: var(--warning-color);
    color: var(--dark-color);
}

.status-approved {
    background-color: var(--success-color);
    color: white;
}

.status-rejected {
    background-color: var(--danger-color);
    color: white;
}

.status-scheduled {
    background-color: var(--primary-color);
    color: white;
}

.status-completed {
    background-color: var(--success-color);
    color: white;
}

.status-cancelled {
    background-color: var(--danger-color);
    color: white;
}

/* Responsive adjustments */
@media (max-width: 767.98px) {
    .card-title {
        font-size: 1.25rem;
    }
    
    .display-4 {
        font-size: 2rem;
    }
    
    .lead {
        font-size: 1rem;
    }
}

FICHIER: static\js\admin.js
/**
 * Anecoop Formations - Admin JavaScript
 * --------------------------
 * Fichier JavaScript pour les fonctionnalités d'administration
 */

// Initialisation lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des tableaux de données
    initDataTables();
    
    // Initialisation du calendrier administrateur si présent
    const adminCalendarEl = document.getElementById('admin-calendar');
    if (adminCalendarEl) {
        initAdminCalendar(adminCalendarEl);
    }
    
    // Initialisation des graphiques si présents
    initCharts();
    
    // Initialisation des datepickers et timepickers
    initDateTimePickers();
    
    // Gestion des actions batch
    initBatchActions();
    
    // Gestion des formulaires avec validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Gestion des alertes auto-fermantes
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-success, .alert.alert-info');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

/**
 * Initialise tous les tableaux de données avec DataTables
 */
function initDataTables() {
    const datatables = document.querySelectorAll('.datatable');
    
    datatables.forEach(table => {
        const options = {
            language: {
                url: '//cdn.datatables.net/plug-ins/1.11.5/i18n/fr-FR.json'
            },
            pageLength: 25,
            responsive: true,
            ordering: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            initComplete: function() {
                // Ajouter des tooltips aux boutons d'action
                const actionButtons = table.querySelectorAll('.action-btn');
                actionButtons.forEach(btn => {
                    new bootstrap.Tooltip(btn);
                });
            }
        };
        
        // Options spécifiques pour certains tableaux
        if (table.id === 'proposals-table') {
            options.order = [[5, 'desc']]; // Trier par date de création descendante
        } else if (table.id === 'sessions-table') {
            options.order = [[2, 'asc']]; // Trier par date croissante
        } else if (table.id === 'documents-table') {
            options.order = [[5, 'desc']]; // Trier par date d'upload descendante
        }
        
        $(table).DataTable(options);
    });
}

/**
 * Initialise le calendrier administrateur avec FullCalendar
 * @param {HTMLElement} calendarEl - L'élément DOM pour le calendrier
 */
function initAdminCalendar(calendarEl) {
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
        },
        locale: 'fr',
        buttonText: {
            today: "Aujourd'hui",
            month: 'Mois',
            week: 'Semaine',
            day: 'Jour',
            list: 'Liste'
        },
        firstDay: 1, // Lundi comme premier jour
        allDaySlot: false,
        slotMinTime: '08:00:00',
        slotMaxTime: '20:00:00',
        slotDuration: '00:30:00',
        navLinks: true,
        editable: true,
        selectable: true,
        dayMaxEvents: true,
        nowIndicator: true,
        businessHours: {
            daysOfWeek: [1, 2, 3, 4, 5], // Lundi - Vendredi
            startTime: '09:00',
            endTime: '18:00',
        },
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        events: {
            url: '/api/sessions',
            method: 'GET'
        },
        eventClick: function(info) {
            if (info.event.url) {
                window.location.href = info.event.url;
                info.jsEvent.preventDefault();
            }
        },
        select: function(info) {
            // Calculer la durée par défaut (1h30)
            const defaultEndTime = new Date(info.start.getTime() + (90 * 60000));
            
            // Ouvrir le modal de création d'événement
            const modal = new bootstrap.Modal(document.getElementById('createSessionModal'));
            
            document.getElementById('session-start-date').value = formatDate(info.start);
            document.getElementById('session-start-time').value = formatTime(info.start);
            document.getElementById('session-end-time').value = formatTime(defaultEndTime);
            
            modal.show();
        },
        eventDrop: function(info) {
            if (confirm(`Êtes-vous sûr de vouloir déplacer "${info.event.title}" au ${formatDateTime(info.event.start)} ?`)) {
                // Appel API pour mettre à jour la session
                updateSessionTime(
                    info.event.id,
                    info.event.start,
                    info.event.end || new Date(info.event.start.getTime() + (90 * 60000))
                );
            } else {
                info.revert();
            }
        },
        eventResize: function(info) {
            if (confirm(`Êtes-vous sûr de vouloir modifier la durée de "${info.event.title}" ?`)) {
                // Appel API pour mettre à jour la session
                updateSessionTime(
                    info.event.id,
                    info.event.start,
                    info.event.end
                );
            } else {
                info.revert();
            }
        },
        loading: function(isLoading) {
            if (isLoading) {
                calendarEl.classList.add('loading');
                const loadingEl = document.createElement('div');
                loadingEl.className = 'calendar-loading-indicator';
                loadingEl.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Chargement...</span></div>';
                calendarEl.appendChild(loadingEl);
            } else {
                calendarEl.classList.remove('loading');
                const loadingEl = calendarEl.querySelector('.calendar-loading-indicator');
                if (loadingEl) loadingEl.remove();
            }
        }
    });
    
    calendar.render();
    
    // Ajouter des filtres pour le calendrier
    const filterForm = document.getElementById('calendar-filters');
    if (filterForm) {
        filterForm.addEventListener('change', function() {
            const serviceId = document.getElementById('filter-service').value;
            const status = document.getElementById('filter-status').value;
            
            calendar.getEvents().forEach(event => {
                let show = true;
                
                if (serviceId && event.extendedProps.serviceId !== serviceId) {
                    show = false;
                }
                
                if (status && event.extendedProps.status !== status) {
                    show = false;
                }
                
                event.setProp('display', show ? 'auto' : 'none');
            });
        });
    }
}

/**
 * Initialise les graphiques Chart.js pour les analytiques
 */
function initCharts() {
    // Graphique des sessions par service
    const sessionsChartEl = document.getElementById('sessions-chart');
    if (sessionsChartEl) {
        const ctx = sessionsChartEl.getContext('2d');
        const data = JSON.parse(sessionsChartEl.dataset.chartData);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Sessions',
                    data: data.values,
                    backgroundColor: data.colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y + ' sessions';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Graphique des participants par mois
    const participantsChartEl = document.getElementById('participants-chart');
    if (participantsChartEl) {
        const ctx = participantsChartEl.getContext('2d');
        const data = JSON.parse(participantsChartEl.dataset.chartData);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Participants',
                    data: data.values,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Graphique circulaire des propositions
    const proposalsChartEl = document.getElementById('proposals-chart');
    if (proposalsChartEl) {
        const ctx = proposalsChartEl.getContext('2d');
        const data = JSON.parse(proposalsChartEl.dataset.chartData);
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['En attente', 'Approuvées', 'Rejetées'],
                datasets: [{
                    data: [data.pending, data.approved, data.rejected],
                    backgroundColor: ['#ffc107', '#198754', '#dc3545']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

/**
 * Initialise les sélecteurs de date et heure
 */
function initDateTimePickers() {
    // Flatpickr pour les dates
    const datePickers = document.querySelectorAll('.date-picker');
    if (datePickers.length) {
        datePickers.forEach(picker => {
            flatpickr(picker, {
                locale: 'fr',
                dateFormat: 'd/m/Y',
                disableMobile: true,
                allowInput: true
            });
        });
    }
    
    // Flatpickr pour les heures
    const timePickers = document.querySelectorAll('.time-picker');
    if (timePickers.length) {
        timePickers.forEach(picker => {
            flatpickr(picker, {
                enableTime: true,
                noCalendar: true,
                dateFormat: 'H:i',
                time_24hr: true,
                minuteIncrement: 15,
                disableMobile: true,
                allowInput: true
            });
        });
    }
    
    // Flatpickr pour les dates et heures
    const dateTimePickers = document.querySelectorAll('.datetime-picker');
    if (dateTimePickers.length) {
        dateTimePickers.forEach(picker => {
            flatpickr(picker, {
                enableTime: true,
                dateFormat: 'd/m/Y H:i',
                time_24hr: true,
                minuteIncrement: 15,
                disableMobile: true,
                allowInput: true,
                locale: 'fr'
            });
        });
    }
}

/**
 * Initialise les actions batch pour les tableaux de données
 */
function initBatchActions() {
    const batchForms = document.querySelectorAll('.batch-action-form');
    
    batchForms.forEach(form => {
        const checkboxes = form.querySelectorAll('.batch-checkbox');
        const selectAll = form.querySelector('.batch-select-all');
        const actionButton = form.querySelector('.batch-action-button');
        
        // Gestion de la case à cocher "Tout sélectionner"
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = selectAll.checked;
                });
                updateBatchActionButton();
            });
        }
        
        // Gestion des cases à cocher individuelles
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateBatchActionButton);
        });
        
        // Mise à jour du bouton d'action
        function updateBatchActionButton() {
            const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            
            if (actionButton) {
                if (checkedCount > 0) {
                    actionButton.disabled = false;
                    actionButton.textContent = `Appliquer (${checkedCount})`;
                } else {
                    actionButton.disabled = true;
                    actionButton.textContent = 'Appliquer';
                }
            }
            
            // Mettre à jour l'état de "Tout sélectionner"
            if (selectAll) {
                selectAll.checked = checkedCount === checkboxes.length && checkboxes.length > 0;
                selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
            }
        }
        
        // Confirmation avant soumission
        form.addEventListener('submit', function(e) {
            const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            const action = form.querySelector('.batch-action-select').value;
            
            if (checkedCount === 0) {
                e.preventDefault();
                alert('Veuillez sélectionner au moins un élément.');
                return false;
            }
            
            if (!confirm(`Êtes-vous sûr de vouloir ${action} ${checkedCount} élément(s) ?`)) {
                e.preventDefault();
                return false;
            }
            
            return true;
        });
    });
}

/**
 * Met à jour l'heure d'une session via API
 * @param {string} sessionId - ID de la session
 * @param {Date} startTime - Nouvelle heure de début
 * @param {Date} endTime - Nouvelle heure de fin
 */
function updateSessionTime(sessionId, startTime, endTime) {
    fetch(`/api/session/${sessionId}/update-time`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            start_time: startTime.toISOString(),
            end_time: endTime.toISOString()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Afficher une notification de succès
            showNotification('Session mise à jour avec succès', 'success');
        } else {
            // Afficher une notification d'erreur
            showNotification(`Erreur: ${data.message}`, 'danger');
            // Rafraîchir le calendrier pour annuler les changements
            calendar.refetchEvents();
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion au serveur', 'danger');
        // Rafraîchir le calendrier pour annuler les changements
        calendar.refetchEvents();
    });
}

/**
 * Affiche une notification temporaire
 * @param {string} message - Message à afficher
 * @param {string} type - Type de notification (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
    const container = document.createElement('div');
    container.className = 'position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1050';
    
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fermer"></button>
        </div>
    `;
    
    container.appendChild(toastEl);
    document.body.appendChild(container);
    
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
    
    // Nettoyer après la fermeture
    toastEl.addEventListener('hidden.bs.toast', function() {
        container.remove();
    });
}

/**
 * Formate une date en format français (JJ/MM/AAAA)
 * @param {Date} date - Date à formater
 * @returns {string} - Date formatée
 */
function formatDate(date) {
    return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
}

/**
 * Formate une heure en format 24h (HH:MM)
 * @param {Date} date - Date à formater
 * @returns {string} - Heure formatée
 */
function formatTime(date) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

/**
 * Formate une date et heure en format français
 * @param {Date} date - Date à formater
 * @returns {string} - Date et heure formatées
 */
function formatDateTime(date) {
    return `${formatDate(date)} ${formatTime(date)}`;
}

/**
 * Prévisualise une image avant upload
 * @param {HTMLInputElement} input - L'élément input file
 * @param {string} previewId - ID de l'élément qui affichera la prévisualisation
 */
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.classList.remove('d-none');
        }
        
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.src = '';
        preview.classList.add('d-none');
    }
}

/**
 * Vérifie et affiche la taille d'un fichier
 * @param {HTMLInputElement} input - L'élément input file
 * @param {string} sizeInfoId - ID de l'élément qui affichera l'info de taille
 * @param {number} maxSize - Taille maximale en octets
 */
function checkFileSize(input, sizeInfoId, maxSize = 16777216) {
    const sizeInfo = document.getElementById(sizeInfoId);
    if (input.files && input.files[0]) {
        const fileSize = input.files[0].size;
        const fileSizeMB = (fileSize / 1024 / 1024).toFixed(2);
        const maxSizeMB = (maxSize / 1024 / 1024).toFixed(2);
        
        if (fileSize > maxSize) {
            sizeInfo.innerHTML = `<span class="text-danger">Fichier trop volumineux: ${fileSizeMB} Mo (max: ${maxSizeMB} Mo)</span>`;
            input.value = ''; // Vider l'input
        } else {
            sizeInfo.innerHTML = `Taille du fichier: ${fileSizeMB} Mo`;
        }
    } else {
        sizeInfo.innerHTML = '';
    }
}


FICHIER: static\js\main.js
/**
 * Anecoop Formations - Main JavaScript (simplifié)
 * --------------------------
 * Fichier JavaScript principal pour les fonctionnalités du front-end
 */

// Initialisation lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialisation des popovers Bootstrap
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Gestion du formulaire de proposition avec validation
    const proposalForms = document.querySelectorAll('.needs-validation');
    Array.from(proposalForms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Gestion des alerts auto-fermantes
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-success, .alert.alert-info');
        alerts.forEach(alert => {
            if (bootstrap && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
});

FICHIER: templates\admin\dashboard.html
{% extends "layout.html" %}

{% block title %}Documents - {{ app_name }}{% endblock %}

{% block extra_css %}
<style>
    .document-card {
        transition: all 0.3s ease;
    }
    .document-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .document-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .document-header {
        height: 8px;
        border-top-left-radius: 0.375rem;
        border-top-right-radius: 0.375rem;
    }
    .filter-container {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }
</style>
{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Documents</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-lg-10 mx-auto">
            <h1 class="h3 mb-4">Documents des formations</h1>
            
            <div class="filter-container">
                <h5 class="mb-3">Filtrer les documents</h5>
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="filter-service" class="form-label">Service</label>
                        <select id="filter-service" class="form-select">
                            <option value="">Tous les services</option>
                            {% for service in services %}
                                <option value="{{ service.id }}">{{ service.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="filter-training" class="form-label">Formation</label>
                        <select id="filter-training" class="form-select">
                            <option value="">Toutes les formations</option>
                            {% for training in trainings %}
                                <option value="{{ training.id }}">{{ training.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="filter-type" class="form-label">Type de fichier</label>
                        <select id="filter-type" class="form-select">
                            <option value="">Tous les types</option>
                            <option value="pdf">PDF</option>
                            <option value="docx">Word</option>
                            <option value="pptx">PowerPoint</option>
                            <option value="xlsx">Excel</option>
                        </select>
                    </div>
                </div>
            </div>
            
            {% if documents %}
                <div class="row row-cols-1 row-cols-md-3 g-4" id="documents-container">
                    {% for document in documents %}
                        <div class="col document-item" 
                             data-service="{{ document.training.service_id }}"
                             data-training="{{ document.training_id }}"
                             data-type="{{ document.file_type }}">
                            <div class="card h-100 document-card">
                                <div class="document-header" style="background-color: {{ document.training.service.color }};"></div>
                                <div class="card-body text-center">
                                    <div class="document-icon">
                                        {% if document.file_type == 'pdf' %}
                                            <i class="fas fa-file-pdf text-danger"></i>
                                        {% elif document.file_type in ['doc', 'docx'] %}
                                            <i class="fas fa-file-word text-primary"></i>
                                        {% elif document.file_type in ['ppt', 'pptx'] %}
                                            <i class="fas fa-file-powerpoint text-warning"></i>
                                        {% elif document.file_type in ['xls', 'xlsx'] %}
                                            <i class="fas fa-file-excel text-success"></i>
                                        {% else %}
                                            <i class="fas fa-file-alt text-secondary"></i>
                                        {% endif %}
                                    </div>
                                    <h5 class="card-title">{{ document.name }}</h5>
                                    <p class="card-text">
                                        <span class="badge rounded-pill" style="background-color: {{ document.training.service.color }};">
                                            {{ document.training.service.name }}
                                        </span>
                                    </p>
                                    <p class="card-text">
                                        <small class="text-muted">{{ document.training.name }}</small>
                                    </p>
                                    {% if document.description %}
                                        <p class="card-text">{{ document.description }}</p>
                                    {% endif %}
                                    <p class="card-text">
                                        <small class="text-muted">Taille: {{ document.file_size|filesizeformat }}</small><br>
                                        <small class="text-muted">Ajouté le: {{ document.created_at.strftime('%d/%m/%Y') }}</small>
                                    </p>
                                </div>
                                <div class="card-footer bg-transparent border-top-0">
                                    <button onclick="downloadDocument('{{ document.id }}', '{{ document.name }}')" class="btn btn-outline-primary w-100">
                                        <i class="fas fa-download me-2"></i>Télécharger
                                    </button>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Aucun document n'est disponible actuellement.
                </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Modal pour le téléchargement -->
<div class="modal fade" id="downloadModal" tabindex="-1" aria-labelledby="downloadModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="downloadModalLabel">Télécharger le document</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>Vous allez télécharger le document <strong id="documentNameSpan"></strong>.</p>
                <p>Veuillez entrer votre email pour que nous puissions suivre le téléchargement:</p>
                <form id="downloadForm">
                    <input type="hidden" id="documentIdInput">
                    <div class="mb-3">
                        <label for="emailInput" class="form-label">Email</label>
                        <input type="email" class="form-control" id="emailInput" required>
                    </div>
                    <div class="mb-3">
                        <label for="nameInput" class="form-label">Nom (optionnel)</label>
                        <input type="text" class="form-control" id="nameInput">
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-download me-1"></i> Télécharger
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Filtrage des documents
        const serviceFilter = document.getElementById('filter-service');
        const trainingFilter = document.getElementById('filter-training');
        const typeFilter = document.getElementById('filter-type');
        const documentsContainer = document.getElementById('documents-container');
        
        if (serviceFilter && trainingFilter && typeFilter && documentsContainer) {
            const filterDocuments = function() {
                const serviceValue = serviceFilter.value;
                const trainingValue = trainingFilter.value;
                const typeValue = typeFilter.value;
                
                const documents = documentsContainer.querySelectorAll('.document-item');
                
                documents.forEach(document => {
                    let showDocument = true;
                    
                    if (serviceValue && document.getAttribute('data-service') !== serviceValue) {
                        showDocument = false;
                    }
                    
                    if (trainingValue && document.getAttribute('data-training') !== trainingValue) {
                        showDocument = false;
                    }
                    
                    if (typeValue && document.getAttribute('data-type') !== typeValue) {
                        showDocument = false;
                    }
                    
                    document.style.display = showDocument ? '' : 'none';
                });
            };
            
            serviceFilter.addEventListener('change', filterDocuments);
            trainingFilter.addEventListener('change', filterDocuments);
            typeFilter.addEventListener('change', filterDocuments);
        }
    });
</script>
{% endblock %}

FICHIER: templates\admin\edit_training.html
{% extends "admin/layout.html" %}

{% block title %}Modifier la formation - Administration {{ app_name }}{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{{ url_for('admin.dashboard') }}">Tableau de bord</a></li>
                <li class="breadcrumb-item"><a href="{{ url_for('admin.manage_trainings') }}">Formations</a></li>
                <li class="breadcrumb-item active" aria-current="page">Modifier {{ training.name }}</li>
            </ol>
        </nav>
        <h1 class="h3">Modifier la formation</h1>
        <p class="text-muted">Modifier les détails de la formation {{ training.name }}.</p>
    </div>
    <div class="col-auto">
        <a href="{{ url_for('main.training_details', training_id=training.id) }}" target="_blank" class="btn btn-outline-primary">
            <i class="fas fa-eye me-1"></i> Voir la formation
        </a>
    </div>
</div>

<div class="row">
    <div class="col-lg-8">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Informations de la formation</h5>
            </div>
            <div class="card-body">
                <form action="{{ url_for('admin.edit_training', training_id=training.id) }}" method="post" class="needs-validation" novalidate>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label for="name" class="form-label">Nom de la formation <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="name" name="name" value="{{ training.name }}" required>
                            <div class="invalid-feedback">
                                Veuillez entrer un nom pour la formation.
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="service_id" class="form-label">Service <span class="text-danger">*</span></label>
                            <select class="form-select" id="service_id" name="service_id" required>
                                {% for service in services %}
                                    <option value="{{ service.id }}" {% if service.id == training.service_id %}selected{% endif %}>
                                        {{ service.name }}
                                    </option>
                                {% endfor %}
                            </select>
                            <div class="invalid-feedback">
                                Veuillez sélectionner un service.
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="duration" class="form-label">Durée (minutes) <span class="text-danger">*</span></label>
                            <input type="number" class="form-control" id="duration" name="duration" min="15" step="15" value="{{ training.duration }}" required>
                            <div class="invalid-feedback">
                                Veuillez entrer une durée valide.
                            </div>
                            <div class="form-text">Exemple: 90 minutes = 1h30</div>
                        </div>
                        <div class="col-md-6">
                            <label for="id" class="form-label">ID</label>
                            <input type="text" class="form-control" id="id" value="{{ training.id }}" readonly disabled>
                            <div class="form-text">L'ID ne peut pas être modifié après la création</div>
                        </div>
                        <div class="col-12">
                            <label for="description" class="form-label">Description</label>
                            <textarea class="form-control" id="description" name="description" rows="4">{{ training.description or '' }}</textarea>
                        </div>
                        <div class="col-12 mt-4">
                            <div class="d-flex justify-content-between">
                                <a href="{{ url_for('admin.manage_trainings') }}" class="btn btn-secondary">Annuler</a>
                                <div>
                                    <button type="button" class="btn btn-danger me-2" data-bs-toggle="modal" data-bs-target="#deleteTrainingModal">
                                        <i class="fas fa-trash me-1"></i> Supprimer
                                    </button>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-save me-1"></i> Enregistrer
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="card-title mb-0">Statistiques</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Sessions programmées
                        <span class="badge bg-primary rounded-pill">{{ training.sessions|selectattr('status', 'equalto', 'scheduled')|list|length }}</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Sessions terminées
                        <span class="badge bg-success rounded-pill">{{ training.sessions|selectattr('status', 'equalto', 'completed')|list|length }}</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Propositions en attente
                        <span class="badge bg-warning rounded-pill">{{ training.proposals|selectattr('status', 'equalto', 'pending')|list|length if training.proposals is defined else 0 }}</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        Documents
                        <span class="badge bg-info rounded-pill">{{ training.documents|length }}</span>
                    </li>
                </ul>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Actions rapides</h5>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="{{ url_for('admin.manage_sessions') }}?training_id={{ training.id }}" class="btn btn-outline-primary">
                        <i class="fas fa-calendar-alt me-1"></i> Gérer les sessions
                    </a>
                    <a href="{{ url_for('admin.upload_document') }}?training_id={{ training.id }}" class="btn btn-outline-success">
                        <i class="fas fa-file-upload me-1"></i> Ajouter un document
                    </a>
                    <a href="{{ url_for('admin.manage_proposals') }}?training_id={{ training.id }}" class="btn btn-outline-warning">
                        <i class="fas fa-clock me-1"></i> Voir les propositions
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Delete Modal -->
<div class="modal fade" id="deleteTrainingModal" tabindex="-1" aria-labelledby="deleteTrainingModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <form action="{{ url_for('admin.delete_training', training_id=training.id) }}" method="post">
                <div class="modal-header">
                    <h5 class="modal-title" id="deleteTrainingModalLabel">Confirmer la suppression</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Êtes-vous sûr de vouloir supprimer la formation <strong>{{ training.name }}</strong> ?</p>
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Cette action est irréversible et supprimera également toutes les sessions, propositions et documents associés à cette formation.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                    <button type="submit" class="btn btn-danger">
                        <i class="fas fa-trash me-1"></i> Supprimer
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Gestion de la validation des formulaires
        const forms = document.querySelectorAll('.needs-validation');
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    });
</script>
{% endblock %}

FICHIER: templates\admin\layout.html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Administration - {{ app_name }}{% endblock %}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <!-- DataTables -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css">
    <!-- FullCalendar -->
    <link href="https://cdn.jsdelivr.net/npm/fullcalendar@5.10.0/main.min.css" rel="stylesheet">
    <!-- Chart.js -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.css">
    <!-- Admin CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/admin.css') }}">
    <!-- Dark mode stylesheet -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/admin-dark.css') }}" id="dark-mode-stylesheet" disabled>
    {% block extra_css %}{% endblock %}
</head>
<body class="d-flex flex-column min-vh-100" data-bs-theme="light">
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('admin.dashboard') }}">
                <i class="fas fa-user-shield me-2"></i>
                {{ app_name }} - Administration
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarAdmin" aria-controls="navbarAdmin" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarAdmin">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.dashboard' %}active{% endif %}" href="{{ url_for('admin.dashboard') }}">
                            <i class="fas fa-tachometer-alt me-1"></i> Tableau de bord
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_services' %}active{% endif %}" href="{{ url_for('admin.manage_services') }}">
                            <i class="fas fa-building me-1"></i> Services
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_trainings' %}active{% endif %}" href="{{ url_for('admin.manage_trainings') }}">
                            <i class="fas fa-graduation-cap me-1"></i> Formations
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_groups' %}active{% endif %}" href="{{ url_for('admin.manage_groups') }}">
                            <i class="fas fa-users me-1"></i> Groupes
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_sessions' %}active{% endif %}" href="{{ url_for('admin.manage_sessions') }}">
                            <i class="fas fa-calendar-alt me-1"></i> Sessions
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_proposals' %}active{% endif %}" href="{{ url_for('admin.manage_proposals') }}">
                            <i class="fas fa-clock me-1"></i> Propositions
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.manage_documents' %}active{% endif %}" href="{{ url_for('admin.manage_documents') }}">
                            <i class="fas fa-file-alt me-1"></i> Documents
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'admin.analytics' %}active{% endif %}" href="{{ url_for('admin.analytics') }}">
                            <i class="fas fa-chart-bar me-1"></i> Analytiques
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('main.index') }}" target="_blank">
                            <i class="fas fa-home me-1"></i> Site public
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fas fa-cog me-1"></i> Options
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="navbarDropdown">
                            <li>
                                <button id="theme-toggle" class="dropdown-item">
                                    <i class="fas fa-moon me-1"></i> Mode sombre
                                </button>
                            </li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a class="dropdown-item" href="{{ url_for('admin.logout') }}">
                                    <i class="fas fa-sign-out-alt me-1"></i> Déconnexion
                                </a>
                            </li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container-fluid mt-3">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Content -->
    <main class="flex-grow-1 py-4">
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    {% block content %}{% endblock %}
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-light py-3 mt-auto border-top">
        <div class="container-fluid">
            <div class="row">
                <div class="col-md-6">
                    <p class="mb-0">&copy; {{ current_year }} {{ app_name }}. Tous droits réservés.</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p class="mb-0">Version 1.0.0</p>
                </div>
            </div>
        </div>
    </footer>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- DataTables -->
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.5/js/dataTables.bootstrap5.min.js"></script>
    <!-- FullCalendar -->
    <script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.10.0/main.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.10.0/locales/fr.js"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <!-- Admin JS -->
    <script src="{{ url_for('static', filename='js/admin.js') }}"></script>
    <script>
        // Dark mode toggle
        document.addEventListener('DOMContentLoaded', function() {
            const themeToggle = document.getElementById('theme-toggle');
            const darkModeStylesheet = document.getElementById('dark-mode-stylesheet');
            const icon = themeToggle.querySelector('i');
            
            // Check local storage for theme preference
            const currentTheme = localStorage.getItem('admin-theme') || 'light';
            if (currentTheme === 'dark') {
                document.body.setAttribute('data-bs-theme', 'dark');
                darkModeStylesheet.removeAttribute('disabled');
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
            
            // Theme toggle click handler
            themeToggle.addEventListener('click', function() {
                if (document.body.getAttribute('data-bs-theme') === 'dark') {
                    document.body.setAttribute('data-bs-theme', 'light');
                    darkModeStylesheet.setAttribute('disabled', '');
                    localStorage.setItem('admin-theme', 'light');
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                } else {
                    document.body.setAttribute('data-bs-theme', 'dark');
                    darkModeStylesheet.removeAttribute('disabled');
                    localStorage.setItem('admin-theme', 'dark');
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                }
            });
            
            // Initialize DataTables
            $('.datatable').DataTable({
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.11.5/i18n/fr-FR.json'
                },
                responsive: true
            });
        });
    </script>
    {% block extra_js %}{% endblock %}
</body>
</html>

FICHIER: templates\admin\login.html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion - Administration {{ app_name }}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {
            height: 100vh;
            display: flex;
            align-items: center;
            background-color: #f5f5f5;
        }
        .form-signin {
            max-width: 350px;
            padding: 15px;
        }
        .form-signin .form-floating:focus-within {
            z-index: 2;
        }
        .form-signin input[type="password"] {
            margin-bottom: 10px;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
        }
        .logo {
            width: 120px;
            height: auto;
            margin-bottom: 1.5rem;
        }
    </style>
</head>
<body>
    <main class="form-signin w-100 m-auto">
        <div class="card shadow-sm">
            <div class="card-body">
                <div class="text-center mb-4">
                    <img class="logo" src="{{ url_for('static', filename='img/logo.png') }}" alt="{{ app_name }}">
                    <h1 class="h4 mb-3 fw-normal">Administration {{ app_name }}</h1>
                </div>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                <form action="{{ url_for('admin.login') }}" method="POST">
                    <div class="form-floating">
                        <input type="password" class="form-control" id="floatingPassword" name="password" placeholder="Mot de passe" required>
                        <label for="floatingPassword">Mot de passe</label>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-primary w-100" type="submit">
                            <i class="fas fa-sign-in-alt me-2"></i>Connexion
                        </button>
                        <a href="{{ url_for('main.index') }}" class="btn btn-outline-secondary w-100">
                            <i class="fas fa-arrow-left me-2"></i>Retour au site
                        </a>
                    </div>
                </form>
            </div>
        </div>
        <p class="mt-3 text-center text-body-secondary">&copy; {{ current_year }} {{ app_name }}</p>
    </main>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

FICHIER: templates\admin\trainings.html
{% extends "admin/layout.html" %}

{% block title %}Gestion des formations - Administration {{ app_name }}{% endblock %}

{% block extra_css %}
<style>
    .service-badge {
        width: 10px;
        height: 10px;
        display: inline-block;
        border-radius: 50%;
        margin-right: 5px;
    }
</style>
{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <h1 class="h3">Gestion des formations</h1>
        <p class="text-muted">Gérez toutes les formations disponibles pour les différents services.</p>
    </div>
    <div class="col-auto">
        <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addTrainingModal">
            <i class="fas fa-plus me-1"></i> Ajouter une formation
        </button>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-striped table-hover datatable" id="trainings-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Service</th>
                        <th>Nom</th>
                        <th>Durée</th>
                        <th>Sessions</th>
                        <th>Propositions</th>
                        <th>Documents</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for training in trainings %}
                    <tr>
                        <td>{{ training.id }}</td>
                        <td>
                            <span class="service-badge" style="background-color: {{ training.service.color }};"></span>
                            {{ training.service.name }}
                        </td>
                        <td>{{ training.name }}</td>
                        <td>{{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}</td>
                        <td>
                            {% set sessions_count = training.sessions|length %}
                            <span class="badge bg-primary rounded-pill">{{ sessions_count }}</span>
                        </td>
                        <td>
                            {% set proposals_count = training.proposals|length if training.proposals is defined else 0 %}
                            <span class="badge bg-warning rounded-pill">{{ proposals_count }}</span>
                        </td>
                        <td>
                            {% set documents_count = training.documents|length %}
                            <span class="badge bg-info rounded-pill">{{ documents_count }}</span>
                        </td>
                        <td class="action-buttons">
                            <a href="{{ url_for('admin.edit_training', training_id=training.id) }}" class="btn btn-sm btn-outline-primary action-btn" data-bs-toggle="tooltip" data-bs-placement="top" title="Modifier">
                                <i class="fas fa-edit"></i>
                            </a>
                            <button type="button" class="btn btn-sm btn-outline-danger action-btn" data-bs-toggle="modal" data-bs-target="#deleteTrainingModal{{ training.id }}" title="Supprimer">
                                <i class="fas fa-trash"></i>
                            </button>
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="fas fa-ellipsis-v"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li>
                                        <a class="dropdown-item" href="{{ url_for('main.training_details', training_id=training.id) }}" target="_blank">
                                            <i class="fas fa-eye me-1"></i> Voir la formation
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="{{ url_for('admin.upload_document') }}?training_id={{ training.id }}">
                                            <i class="fas fa-file-upload me-1"></i> Ajouter un document
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li>
                                        <a class="dropdown-item" href="{{ url_for('admin.manage_sessions') }}?training_id={{ training.id }}">
                                            <i class="fas fa-calendar-alt me-1"></i> Gérer les sessions
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Delete Modal -->
                    <div class="modal fade" id="deleteTrainingModal{{ training.id }}" tabindex="-1" aria-labelledby="deleteTrainingModalLabel{{ training.id }}" aria-hidden="true">
                        <div class="modal-dialog">
                            <div class="modal-content">
                                <form action="{{ url_for('admin.delete_training', training_id=training.id) }}" method="post">
                                    <div class="modal-header">
                                        <h5 class="modal-title" id="deleteTrainingModalLabel{{ training.id }}">Confirmer la suppression</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <div class="modal-body">
                                        <p>Êtes-vous sûr de vouloir supprimer la formation <strong>{{ training.name }}</strong> ?</p>
                                        <div class="alert alert-warning">
                                            <i class="fas fa-exclamation-triangle me-2"></i>
                                            Cette action est irréversible et supprimera également toutes les sessions, propositions et documents associés à cette formation.
                                        </div>
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                                        <button type="submit" class="btn btn-danger">
                                            <i class="fas fa-trash me-1"></i> Supprimer
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Add Training Modal -->
<div class="modal fade" id="addTrainingModal" tabindex="-1" aria-labelledby="addTrainingModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <form action="{{ url_for('admin.add_training') }}" method="post" class="needs-validation" novalidate>
                <div class="modal-header">
                    <h5 class="modal-title" id="addTrainingModalLabel">Ajouter une formation</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label for="name" class="form-label">Nom de la formation <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="name" name="name" required>
                            <div class="invalid-feedback">
                                Veuillez entrer un nom pour la formation.
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="service_id" class="form-label">Service <span class="text-danger">*</span></label>
                            <select class="form-select" id="service_id" name="service_id" required>
                                <option value="" selected disabled>Choisir un service...</option>
                                {% for service in services %}
                                    <option value="{{ service.id }}">{{ service.name }}</option>
                                {% endfor %}
                            </select>
                            <div class="invalid-feedback">
                                Veuillez sélectionner un service.
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="duration" class="form-label">Durée (minutes) <span class="text-danger">*</span></label>
                            <input type="number" class="form-control" id="duration" name="duration" min="15" step="15" value="90" required>
                            <div class="invalid-feedback">
                                Veuillez entrer une durée valide.
                            </div>
                            <div class="form-text">Par défaut: 1h30 (90 minutes)</div>
                        </div>
                        <div class="col-md-6">
                            <label for="id" class="form-label">ID personnalisé</label>
                            <input type="text" class="form-control" id="id" name="id" placeholder="Généré automatiquement si vide">
                            <div class="form-text">Laisser vide pour générer automatiquement</div>
                        </div>
                        <div class="col-12">
                            <label for="description" class="form-label">Description</label>
                            <textarea class="form-control" id="description" name="description" rows="4"></textarea>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save me-1"></i> Enregistrer
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Initialiser DataTable (déjà fait dans admin.js)
        
        // Gestion de la validation des formulaires
        const forms = document.querySelectorAll('.needs-validation');
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    });
</script>
{% endblock %}

FICHIER: templates\calendar.html
{% extends "layout.html" %}

{% block title %}Calendrier des formations - {{ app_name }}{% endblock %}

{% block extra_css %}
<style>
    .fc-event {
        cursor: pointer;
    }
    
    .calendar-container {
        height: 700px;
    }
    
    .calendar-loading-indicator {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 10;
    }
    
    .filter-container {
        margin-bottom: 20px;
    }
    
    @media (max-width: 767.98px) {
        .calendar-container {
            height: 500px;
        }
        
        .fc .fc-toolbar-title {
            font-size: 1.1rem;
        }
        
        .fc .fc-button {
            padding: 0.2rem 0.4rem;
            font-size: 0.8rem;
        }
    }
</style>
{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Calendrier des formations</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-lg-10 mx-auto">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h1 class="h3 mb-4">Calendrier des formations</h1>
                    
                    <div class="filter-container">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="form-group">
                                    <label for="filter-service" class="form-label">Filtrer par service</label>
                                    <select id="filter-service" class="form-select">
                                        <option value="">Tous les services</option>
                                        {% for service in services %}
                                            <option value="{{ service.id }}">{{ service.name }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="calendar-container">
                        <div id="calendar"></div>
                    </div>
                </div>
                <div class="card-footer bg-light">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="small text-muted">
                                <i class="fas fa-info-circle me-1"></i>
                                Cliquez sur une formation pour voir les détails ou proposer un créneau.
                            </div>
                        </div>
                        <div class="col-md-4 text-md-end">
                            <a href="{{ url_for('main.trainings') }}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-graduation-cap me-1"></i> Voir toutes les formations
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-lg-10 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header bg-light">
                    <h2 class="h5 mb-0">À propos du calendrier</h2>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h3 class="h6">Comment lire le calendrier ?</h3>
                            <p>
                                Le calendrier affiche toutes les sessions de formation programmées. 
                                Chaque couleur correspond à un service différent. Cliquez sur un événement 
                                pour voir les détails de la formation.
                            </p>
                        </div>
                        <div class="col-md-6">
                            <h3 class="h6">Vous ne trouvez pas de créneau qui vous convient ?</h3>
                            <p>
                                Vous pouvez proposer un créneau personnalisé en vous rendant sur la page de la formation 
                                qui vous intéresse et en cliquant sur "Proposer un créneau".
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal pour les détails de l'événement -->
<div class="modal fade" id="eventDetailsModal" tabindex="-1" aria-labelledby="eventDetailsModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="eventDetailsModalLabel">Détails de la formation</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" id="eventDetailsBody">
                <!-- Le contenu sera injecté dynamiquement -->
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                <a href="#" class="btn btn-primary" id="eventDetailLink">Voir la formation</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // La fonction initializeCalendar est définie dans main.js
        const calendarEl = document.getElementById('calendar');
        if (calendarEl) {
            initializeCalendar(calendarEl);
        }
        
        // Gestion du clic sur un événement pour afficher le modal
        calendarEl.addEventListener('eventClick', function(info) {
            if (!info.event.url) {
                const modal = new bootstrap.Modal(document.getElementById('eventDetailsModal'));
                const modalBody = document.getElementById('eventDetailsBody');
                const detailLink = document.getElementById('eventDetailLink');
                
                modalBody.innerHTML = `
                    <div class="mb-3">
                        <h5>${info.event.title}</h5>
                        <p>${info.event.extendedProps.description || 'Aucune description disponible'}</p>
                    </div>
                    <div class="mb-2">
                        <strong>Service:</strong> ${info.event.extendedProps.serviceName || 'Non spécifié'}
                    </div>
                    <div class="mb-2">
                        <strong>Date:</strong> ${info.event.start.toLocaleDateString('fr-FR')}
                    </div>
                    <div class="mb-2">
                        <strong>Horaires:</strong> ${info.event.start.toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'})} - ${info.event.end.toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'})}
                    </div>
                    <div class="mb-2">
                        <strong>Lieu:</strong> ${info.event.extendedProps.location || 'À déterminer'}
                    </div>
                `;
                
                detailLink.href = `/training/${info.event.extendedProps.trainingId}`;
                modal.show();
            }
        });
    });
</script>
{% endblock %}


FICHIER: templates\documents.html
{% extends "layout.html" %}

{% block title %}Documents - {{ app_name }}{% endblock %}

{% block extra_css %}
<style>
    .document-card {
        transition: all 0.3s ease;
    }
    .document-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .document-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .document-header {
        height: 8px;
        border-top-left-radius: 0.375rem;
        border-top-right-radius: 0.375rem;
    }
    .filter-container {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }
</style>
{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Documents</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-lg-10 mx-auto">
            <h1 class="h3 mb-4">Documents des formations</h1>
            
            <div class="filter-container">
                <h5 class="mb-3">Filtrer les documents</h5>
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="filter-service" class="form-label">Service</label>
                        <select id="filter-service" class="form-select">
                            <option value="">Tous les services</option>
                            {% for service in services %}
                                <option value="{{ service.id }}">{{ service.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="filter-training" class="form-label">Formation</label>
                        <select id="filter-training" class="form-select">
                            <option value="">Toutes les formations</option>
                            {% for training in trainings %}
                                <option value="{{ training.id }}">{{ training.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="filter-type" class="form-label">Type de fichier</label>
                        <select id="filter-type" class="form-select">
                            <option value="">Tous les types</option>
                            <option value="pdf">PDF</option>
                            <option value="docx">Word</option>
                            <option value="pptx">PowerPoint</option>
                            <option value="xlsx">Excel</option>
                        </select>
                    </div>
                </div>
            </div>
            
            {% if documents %}
                <div class="row row-cols-1 row-cols-md-3 g-4" id="documents-container">
                    {% for document in documents %}
                        <div class="col document-item" 
                             data-service="{{ document.training.service_id }}"
                             data-training="{{ document.training_id }}"
                             data-type="{{ document.file_type }}">
                            <div class="card h-100 document-card">
                                <div class="document-header" style="background-color: {{ document.training.service.color }};"></div>
                                <div class="card-body text-center">
                                    <div class="document-icon">
                                        {% if document.file_type == 'pdf' %}
                                            <i class="fas fa-file-pdf text-danger"></i>
                                        {% elif document.file_type in ['doc', 'docx'] %}
                                            <i class="fas fa-file-word text-primary"></i>
                                        {% elif document.file_type in ['ppt', 'pptx'] %}
                                            <i class="fas fa-file-powerpoint text-warning"></i>
                                        {% elif document.file_type in ['xls', 'xlsx'] %}
                                            <i class="fas fa-file-excel text-success"></i>
                                        {% else %}
                                            <i class="fas fa-file-alt text-secondary"></i>
                                        {% endif %}
                                    </div>
                                    <h5 class="card-title">{{ document.name }}</h5>
                                    <p class="card-text">
                                        <span class="badge rounded-pill" style="background-color: {{ document.training.service.color }};">
                                            {{ document.training.service.name }}
                                        </span>
                                    </p>
                                    <p class="card-text">
                                        <small class="text-muted">{{ document.training.name }}</small>
                                    </p>
                                    {% if document.description %}
                                        <p class="card-text">{{ document.description }}</p>
                                    {% endif %}
                                    <p class="card-text">
                                        <small class="text-muted">Taille: {{ document.file_size|filesizeformat }}</small><br>
                                        <small class="text-muted">Ajouté le: {{ document.created_at.strftime('%d/%m/%Y') }}</small>
                                    </p>
                                </div>
                                <div class="card-footer bg-transparent border-top-0">
                                    <button onclick="downloadDocument('{{ document.id }}', '{{ document.name }}')" class="btn btn-outline-primary w-100">
                                        <i class="fas fa-download me-2"></i>Télécharger
                                    </button>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Aucun document n'est disponible actuellement.
                </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Modal pour le téléchargement -->
<div class="modal fade" id="downloadModal" tabindex="-1" aria-labelledby="downloadModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="downloadModalLabel">Télécharger le document</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>Vous allez télécharger le document <strong id="documentNameSpan"></strong>.</p>
                <p>Veuillez entrer votre email pour que nous puissions suivre le téléchargement:</p>
                <form id="downloadForm">
                    <input type="hidden" id="documentIdInput">
                    <div class="mb-3">
                        <label for="emailInput" class="form-label">Email</label>
                        <input type="email" class="form-control" id="emailInput" required>
                    </div>
                    <div class="mb-3">
                        <label for="nameInput" class="form-label">Nom (optionnel)</label>
                        <input type="text" class="form-control" id="nameInput">
                    </div>
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-download me-1"></i> Télécharger
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Filtrage des documents
        const serviceFilter = document.getElementById('filter-service');
        const trainingFilter = document.getElementById('filter-training');
        const typeFilter = document.getElementById('filter-type');
        const documentsContainer = document.getElementById('documents-container');
        
        if (serviceFilter && trainingFilter && typeFilter && documentsContainer) {
            const filterDocuments = function() {
                const serviceValue = serviceFilter.value;
                const trainingValue = trainingFilter.value;
                const typeValue = typeFilter.value;
                
                const documents = documentsContainer.querySelectorAll('.document-item');
                
                documents.forEach(document => {
                    let showDocument = true;
                    
                    if (serviceValue && document.getAttribute('data-service') !== serviceValue) {
                        showDocument = false;
                    }
                    
                    if (trainingValue && document.getAttribute('data-training') !== trainingValue) {
                        showDocument = false;
                    }
                    
                    if (typeValue && document.getAttribute('data-type') !== typeValue) {
                        showDocument = false;
                    }
                    
                    document.style.display = showDocument ? '' : 'none';
                });
            };
            
            serviceFilter.addEventListener('change', filterDocuments);
            trainingFilter.addEventListener('change', filterDocuments);
            typeFilter.addEventListener('change', filterDocuments);
        }
    });
</script>
{% endblock %}

FICHIER: templates\errors\403.html
{% extends "layout.html" %}

{% block title %}Accès refusé - {{ app_name }}{% endblock %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-8 mx-auto text-center py-5">
            <div class="mb-4">
                <i class="fas fa-lock text-danger" style="font-size: 5rem;"></i>
            </div>
            <h1 class="h2 mb-4">403 - Accès refusé</h1>
            <p class="lead mb-4">Désolé, vous n'avez pas les autorisations nécessaires pour accéder à cette page.</p>
            <div class="mb-5">
                <a href="{{ url_for('main.index') }}" class="btn btn-primary">
                    <i class="fas fa-home me-2"></i>Retour à l'accueil
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}

FICHIER: templates\errors\404.html
{% extends "layout.html" %}

{% block title %}Page non trouvée - {{ app_name }}{% endblock %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-8 mx-auto text-center py-5">
            <div class="mb-4">
                <i class="fas fa-map-signs text-primary" style="font-size: 5rem;"></i>
            </div>
            <h1 class="h2 mb-4">404 - Page non trouvée</h1>
            <p class="lead mb-4">Désolé, la page que vous recherchez n'existe pas ou a été déplacée.</p>
            <div class="mb-5">
                <a href="{{ url_for('main.index') }}" class="btn btn-primary">
                    <i class="fas fa-home me-2"></i>Retour à l'accueil
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}

FICHIER: templates\errors\500.html
{% extends "layout.html" %}

{% block title %}Erreur serveur - {{ app_name }}{% endblock %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-8 mx-auto text-center py-5">
            <div class="mb-4">
                <i class="fas fa-exclamation-triangle text-warning" style="font-size: 5rem;"></i>
            </div>
            <h1 class="h2 mb-4">500 - Erreur serveur</h1>
            <p class="lead mb-4">Oups ! Une erreur s'est produite sur notre serveur. Notre équipe technique a été informée du problème.</p>
            <div class="mb-5">
                <a href="{{ url_for('main.index') }}" class="btn btn-primary">
                    <i class="fas fa-home me-2"></i>Retour à l'accueil
                </a>
                <button onclick="window.location.reload()" class="btn btn-outline-secondary ms-2">
                    <i class="fas fa-sync-alt me-2"></i>Réessayer
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

FICHIER: templates\index.html
{% extends "layout.html" %}

{% block title %}{{ app_name }} - Accueil{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-5">
        <div class="col-lg-8 mx-auto text-center">
            <h1 class="display-4 fw-bold mb-4">Réservez vos formations internes</h1>
            <p class="lead">Une plateforme simple et efficace pour organiser et participer aux formations internes d'Anecoop France.</p>
            <div class="d-grid gap-2 d-sm-flex justify-content-sm-center mt-4">
                <a href="{{ url_for('main.services') }}" class="btn btn-primary btn-lg px-4 gap-3">Voir les services</a>
                <a href="{{ url_for('main.trainings') }}" class="btn btn-outline-secondary btn-lg px-4">Toutes les formations</a>
            </div>
        </div>
    </div>

    <!-- Services Cards -->
    <h2 class="text-center mb-4">Nos services</h2>
    <div class="row row-cols-1 row-cols-md-3 g-4 mb-5">
        {% for service in services %}
        <div class="col">
            <div class="card h-100 shadow-sm">
                <div class="card-header" style="background-color: {{ service.color }}; height: 8px;"></div>
                <div class="card-body">
                    <h3 class="card-title">{{ service.name }}</h3>
                    <p class="card-text">
                        <strong>Responsable:</strong> {{ service.manager_name }}
                    </p>
                    <a href="{{ url_for('main.service_details', service_id=service.id) }}" class="btn btn-sm" style="background-color: {{ service.color }}; color: white;">
                        Voir les formations
                    </a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <!-- How it works section -->
    <h2 class="text-center mb-4">Comment ça marche ?</h2>
    <div class="row mb-5">
        <div class="col-md-4 text-center mb-4">
            <div class="bg-light p-4 rounded-4 h-100">
                <div class="mb-3">
                    <i class="fas fa-search fa-3x text-primary"></i>
                </div>
                <h3>1. Choisissez une formation</h3>
                <p>Parcourez les formations disponibles par service et trouvez celle qui vous intéresse.</p>
            </div>
        </div>
        <div class="col-md-4 text-center mb-4">
            <div class="bg-light p-4 rounded-4 h-100">
                <div class="mb-3">
                    <i class="fas fa-calendar-alt fa-3x text-primary"></i>
                </div>
                <h3>2. Proposez une date</h3>
                <p>Proposez un créneau qui vous convient pour suivre la formation.</p>
            </div>
        </div>
        <div class="col-md-4 text-center mb-4">
            <div class="bg-light p-4 rounded-4 h-100">
                <div class="mb-3">
                    <i class="fas fa-check-circle fa-3x text-primary"></i>
                </div>
                <h3>3. Recevez confirmation</h3>
                <p>Après validation, vous recevrez une confirmation par email avec tous les détails.</p>
            </div>
        </div>
    </div>
    
    <!-- Call to action -->
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <div class="card border-primary mb-5">
                <div class="card-body text-center">
                    <h3 class="card-title">Prêt à améliorer vos compétences ?</h3>
                    <p class="card-text">Consultez le calendrier des formations et proposez votre participation dès maintenant.</p>
                    <a href="{{ url_for('main.calendar') }}" class="btn btn-primary">Voir le calendrier</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

FICHIER: templates\layout.html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <!-- Dark mode stylesheet -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/dark-mode.css') }}" id="dark-mode-stylesheet" disabled>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-light bg-light shadow-sm">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('main.index') }}">
                <span class="me-2 text-primary"><i class="fas fa-book"></i></span>
                {{ app_name }}
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'main.index' %}active{% endif %}" href="{{ url_for('main.index') }}">Accueil</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'main.services' %}active{% endif %}" href="{{ url_for('main.services') }}">Services</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'main.trainings' %}active{% endif %}" href="{{ url_for('main.trainings') }}">Formations</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'main.calendar' %}active{% endif %}" href="{{ url_for('main.calendar') }}">Calendrier</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'main.documents' %}active{% endif %}" href="{{ url_for('main.documents') }}">Documents</a>
                    </li>
                    {% if session.get('admin_logged_in') %}
                    <li class="nav-item">
                        <a class="nav-link btn btn-primary text-white" href="{{ url_for('admin.dashboard') }}">Administration</a>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('admin.login') }}">Administration</a>
                    </li>
                    {% endif %}
                    <li class="nav-item ms-2">
                        <button id="theme-toggle" class="btn btn-outline-secondary">
                            <i class="fas fa-moon"></i>
                        </button>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="container mt-3">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Content -->
    <main class="flex-grow-1 py-4">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-light py-4 mt-auto">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <p class="mb-0">&copy; {{ current_year }} {{ app_name }}. Tous droits réservés.</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p class="mb-0">Développé avec <i class="fas fa-heart text-danger"></i> pour Anecoop</p>
                </div>
            </div>
        </div>
    </footer>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- Custom JS -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    <script>
        // Dark mode toggle
        document.addEventListener('DOMContentLoaded', function() {
            const themeToggle = document.getElementById('theme-toggle');
            const darkModeStylesheet = document.getElementById('dark-mode-stylesheet');
            const icon = themeToggle.querySelector('i');
            
            // Check local storage for theme preference
            const currentTheme = localStorage.getItem('theme') || 'light';
            if (currentTheme === 'dark') {
                document.body.setAttribute('data-bs-theme', 'dark');
                darkModeStylesheet.removeAttribute('disabled');
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            }
            
            // Theme toggle click handler
            themeToggle.addEventListener('click', function() {
                if (document.body.getAttribute('data-bs-theme') === 'dark') {
                    document.body.setAttribute('data-bs-theme', 'light');
                    darkModeStylesheet.setAttribute('disabled', '');
                    localStorage.setItem('theme', 'light');
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                } else {
                    document.body.setAttribute('data-bs-theme', 'dark');
                    darkModeStylesheet.removeAttribute('disabled');
                    localStorage.setItem('theme', 'dark');
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                }
            });
        });
    </script>
    {% block extra_js %}{% endblock %}
</body>
</html>

FICHIER: templates\propose_time.html
{% extends "layout.html" %}

{% block title %}Proposer un créneau - {{ training.name }}{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
<style>
    .time-picker-container {
        position: relative;
    }
    .flatpickr-input {
        background-color: white !important;
    }
    .form-card {
        max-width: 800px;
        margin: 0 auto;
    }
    .service-color {
        width: 8px;
        height: 100%;
        position: absolute;
        left: 0;
        top: 0;
        background-color: {{ training.service.color }};
    }
</style>
{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.services') }}">Services</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.service_details', service_id=training.service.id) }}">{{ training.service.name }}</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.training_details', training_id=training.id) }}">{{ training.name }}</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Proposer un créneau</li>
                </ol>
            </nav>
        </div>
    </div>

    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm form-card">
                <div class="card-body position-relative">
                    <div class="service-color"></div>
                    <div class="p-3">
                        <h1 class="h3 mb-4">Proposer un créneau pour "{{ training.name }}"</h1>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Cette formation dure <strong>{{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}</strong>. Veuillez proposer un créneau qui convient à votre emploi du temps.
                        </div>
                        
                        <form method="post" class="needs-validation" novalidate>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label for="name" class="form-label">Nom complet <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="name" name="name" required>
                                    <div class="invalid-feedback">
                                        Veuillez entrer votre nom.
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label for="email" class="form-label">Email <span class="text-danger">*</span></label>
                                    <input type="email" class="form-control" id="email" name="email" placeholder="nom@anecoop-france.com" required>
                                    <div class="invalid-feedback">
                                        Veuillez entrer une adresse email valide.
                                    </div>
                                </div>
                                
                                <div class="col-md-12">
                                    <label for="department" class="form-label">Département / Service</label>
                                    <input type="text" class="form-control" id="department" name="department">
                                </div>
                                
                                <div class="col-md-6">
                                    <label for="date" class="form-label">Date <span class="text-danger">*</span></label>
                                    <div class="input-group">
                                        <span class="input-group-text"><i class="fas fa-calendar-alt"></i></span>
                                        <input type="text" class="form-control date-picker" id="date" name="date" placeholder="JJ/MM/AAAA" required>
                                    </div>
                                    <div class="invalid-feedback">
                                        Veuillez sélectionner une date.
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <label for="time" class="form-label">Heure <span class="text-danger">*</span></label>
                                    <div class="input-group">
                                        <span class="input-group-text"><i class="fas fa-clock"></i></span>
                                        <input type="text" class="form-control time-picker" id="time" name="time" placeholder="HH:MM" required>
                                    </div>
                                    <div class="invalid-feedback">
                                        Veuillez sélectionner une heure.
                                    </div>
                                </div>
                            </div>
                            
                            <div class="my-4">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="agreement" required>
                                    <label class="form-check-label" for="agreement">
                                        Je comprends que je serai notifié(e) par email lorsque ma proposition sera traitée.
                                    </label>
                                    <div class="invalid-feedback">
                                        Vous devez accepter pour continuer.
                                    </div>
                                </div>
                            </div>
                            
                            <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                                <a href="{{ url_for('main.training_details', training_id=training.id) }}" class="btn btn-outline-secondary">Annuler</a>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-paper-plane me-1"></i> Envoyer ma proposition
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                <div class="card-footer bg-light">
                    <small class="text-muted">
                        <i class="fas fa-info-circle me-1"></i> 
                        Votre proposition sera examinée par l'administrateur. Vous recevrez une notification par email.
                    </small>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header bg-light">
                    <h2 class="h5 mb-0">À propos de cette formation</h2>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <h3 class="h6 fw-bold">{{ training.name }}</h3>
                        <p>{{ training.description }}</p>
                    </div>
                    <div class="mb-3">
                        <h3 class="h6 fw-bold">Durée</h3>
                        <p>{{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}</p>
                    </div>
                    <div>
                        <h3 class="h6 fw-bold">Responsable du service</h3>
                        <p>{{ training.service.manager_name }} ({{ training.service.manager_email }})</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
<script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/fr.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Date picker configuration
        flatpickr('.date-picker', {
            locale: 'fr',
            dateFormat: 'd/m/Y',
            minDate: 'today',
            disableMobile: true
        });
        
        // Time picker configuration
        flatpickr('.time-picker', {
            enableTime: true,
            noCalendar: true,
            dateFormat: 'H:i',
            time_24hr: true,
            minuteIncrement: 30,
            disableMobile: true
        });
        
        // Form validation
        const forms = document.querySelectorAll('.needs-validation');
        
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    });
</script>
{% endblock %}

FICHIER: templates\service_details.html
{% extends "layout.html" %}

{% block title %}{{ service.name }} - {{ app_name }}{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.services') }}">Services</a></li>
                    <li class="breadcrumb-item active" aria-current="page">{{ service.name }}</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header" style="background-color: {{ service.color }}; height: 8px;"></div>
                <div class="card-body">
                    <h1 class="card-title h3">{{ service.name }}</h1>
                    <p class="card-text mb-3">
                        <strong>Responsable:</strong> {{ service.manager_name }}<br>
                        <strong>Email:</strong> <a href="mailto:{{ service.manager_email }}">{{ service.manager_email }}</a>
                    </p>
                    
                    <h2 class="h5 mt-4 mb-3">Formations disponibles</h2>
                    {% if trainings %}
                        <div class="list-group">
                            {% for training in trainings %}
                                <a href="{{ url_for('main.training_details', training_id=training.id) }}" class="list-group-item list-group-item-action">
                                    <div class="d-flex w-100 justify-content-between">
                                        <h3 class="mb-1 h6">{{ training.name }}</h3>
                                        <small class="text-muted">{{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}</small>
                                    </div>
                                    <p class="mb-1">{{ training.description }}</p>
                                    <small>
                                        <span class="badge rounded-pill" style="background-color: {{ service.color }};">
                                            {{ service.name }}
                                        </span>
                                    </small>
                                </a>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Aucune formation n'est disponible pour ce service actuellement.
                        </div>
                    {% endif %}
                </div>
                <div class="card-footer bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i> 
                            Pour proposer un créneau, sélectionnez une formation.
                        </small>
                        <a href="{{ url_for('main.services') }}" class="btn btn-outline-secondary btn-sm">
                            <i class="fas fa-arrow-left me-1"></i> Retour aux services
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Contact du responsable -->
    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm border-light">
                <div class="card-body">
                    <h2 class="h5 card-title mb-3">Besoin d'informations complémentaires ?</h2>
                    <p class="card-text">
                        Pour toute question concernant les formations du service {{ service.name }}, 
                        n'hésitez pas à contacter le responsable <strong>{{ service.manager_name }}</strong> 
                        via <a href="mailto:{{ service.manager_email }}">{{ service.manager_email }}</a>.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}


FICHIER: templates\track_proposal.html
{% extends "layout.html" %}

{% block title %}Suivi de proposition - {{ app_name }}{% endblock %}

{% block extra_css %}
<style>
    .status-circle {
        display: inline-block;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        margin-right: 10px;
    }
    .status-pending {
        background-color: #ffc107;
    }
    .status-approved {
        background-color: #198754;
    }
    .status-rejected {
        background-color: #dc3545;
    }
    .status-container {
        display: flex;
        align-items: center;
    }
    .tracking-card {
        max-width: 800px;
        margin: 0 auto;
    }
</style>
{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Suivi de proposition</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm tracking-card" id="tracking-container" data-proposal-id="{{ proposal.id }}">
                <div class="card-header" style="background-color: {{ proposal.training.service.color }}; height: 8px;"></div>
                <div class="card-body">
                    <h1 class="h3 mb-4">Suivi de votre proposition</h1>
                    
                    <div class="card mb-4">
                        <div class="card-body">
                            <h2 class="h5 mb-3">Détails de la demande</h2>
                            
                            <div class="row">
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Formation:</strong></p>
                                    <p>{{ proposal.training.name }}</p>
                                </div>
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Service:</strong></p>
                                    <p>{{ proposal.training.service.name }}</p>
                                </div>
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Durée:</strong></p>
                                    <p>{{ proposal.training.duration // 60 }}h{{ '30' if proposal.training.duration % 60 > 0 else '00' }}</p>
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Date proposée:</strong></p>
                                    <p>{{ proposal.proposed_time.strftime('%d/%m/%Y') }}</p>
                                </div>
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Heure proposée:</strong></p>
                                    <p>{{ proposal.proposed_time.strftime('%H:%M') }}</p>
                                </div>
                                <div class="col-md-4">
                                    <p class="mb-1"><strong>Demandeur:</strong></p>
                                    <p>{{ proposal.proposer_name }}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mb-4">
                        <div class="card-body">
                            <h2 class="h5 mb-3">Statut actuel</h2>
                            
                            <div class="status-container mb-3 proposal-status">
                                <span class="status-circle status-{{ proposal.status }}"></span>
                                <span class="status-pill status-{{ proposal.status }}">
                                    {% if proposal.status == 'pending' %}
                                        En attente
                                    {% elif proposal.status == 'approved' %}
                                        Approuvée
                                    {% elif proposal.status == 'rejected' %}
                                        Rejetée
                                    {% endif %}
                                </span>
                            </div>
                            
                            {% if proposal.status == 'pending' %}
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    Votre proposition est en cours d'examen. Vous recevrez une notification par email dès qu'elle sera traitée.
                                </div>
                            {% elif proposal.status == 'approved' %}
                                <div class="alert alert-success">
                                    <i class="fas fa-check-circle me-2"></i>
                                    Votre proposition a été approuvée ! Un email de confirmation vous a été envoyé avec tous les détails.
                                </div>
                                
                                {% if proposal.session %}
                                    <div class="mt-4">
                                        <h3 class="h6">Informations sur la session:</h3>
                                        <ul class="list-group">
                                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                                <span><i class="fas fa-calendar me-2"></i> Date</span>
                                                <span class="badge bg-primary rounded-pill">{{ proposal.session.start_time.strftime('%d/%m/%Y') }}</span>
                                            </li>
                                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                                <span><i class="fas fa-clock me-2"></i> Horaires</span>
                                                <span class="badge bg-primary rounded-pill">{{ proposal.session.start_time.strftime('%H:%M') }} - {{ proposal.session.end_time.strftime('%H:%M') }}</span>
                                            </li>
                                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                                <span><i class="fas fa-map-marker-alt me-2"></i> Lieu</span>
                                                <span class="badge bg-primary rounded-pill">{{ proposal.session.location or 'À déterminer' }}</span>
                                            </li>
                                        </ul>
                                    </div>
                                {% endif %}
                            {% elif proposal.status == 'rejected' %}
                                <div class="alert alert-danger">
                                    <i class="fas fa-times-circle me-2"></i>
                                    Votre proposition n'a pas pu être retenue. Un email vous a été envoyé à ce sujet.
                                </div>
                                
                                <div class="mt-4 text-center">
                                    <a href="{{ url_for('main.propose_time', training_id=proposal.training_id) }}" class="btn btn-primary">
                                        <i class="fas fa-calendar-plus me-1"></i> Faire une nouvelle proposition
                                    </a>
                                </div>
                            {% endif %}
                        </div>
                    </div>
                    
                    {% if proposal.status == 'pending' %}
                        <div class="text-center mb-4">
                            <div class="small text-muted">
                                <i class="fas fa-sync-alt me-1"></i>
                                Cette page se rafraîchit automatiquement. Dernière mise à jour: {{ proposal.updated_at.strftime('%d/%m/%Y %H:%M') }}
                            </div>
                        </div>
                    {% endif %}
                    
                    <div class="d-grid gap-2 d-md-flex justify-content-md-start">
                        <a href="{{ url_for('main.training_details', training_id=proposal.training_id) }}" class="btn btn-outline-secondary">
                            <i class="fas fa-arrow-left me-1"></i> Retour à la formation
                        </a>
                        {% if proposal.status == 'pending' %}
                            <a href="{{ url_for('main.index') }}" class="btn btn-outline-primary">
                                <i class="fas fa-home me-1"></i> Accueil
                            </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}


FICHIER: templates\training_details.html
{% extends "layout.html" %}

{% block title %}{{ training.name }} - {{ app_name }}{% endblock %}

{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.services') }}">Services</a></li>
                    <li class="breadcrumb-item"><a href="{{ url_for('main.service_details', service_id=training.service.id) }}">{{ training.service.name }}</a></li>
                    <li class="breadcrumb-item active" aria-current="page">{{ training.name }}</li>
                </ol>
            </nav>
        </div>
    </div>
    
    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header" style="background-color: {{ training.service.color }}; height: 8px;"></div>
                <div class="card-body">
                    <h1 class="card-title h3">{{ training.name }}</h1>
                    <div class="mb-3">
                        <span class="badge rounded-pill" style="background-color: {{ training.service.color }};">
                            {{ training.service.name }}
                        </span>
                        <span class="badge bg-secondary rounded-pill">
                            <i class="fas fa-clock me-1"></i> {{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}
                        </span>
                    </div>
                    
                    <h2 class="h5 mt-4 mb-2">Description</h2>
                    <p class="card-text">{{ training.description }}</p>
                    
                    {% if training.sessions|length > 0 %}
                        <h2 class="h5 mt-4 mb-2">Sessions à venir</h2>
                        <div class="list-group mb-4">
                            {% for session in upcoming_sessions %}
                                <div class="list-group-item">
                                    <div class="d-flex w-100 justify-content-between">
                                        <h5 class="mb-1">{{ session.start_time.strftime('%d/%m/%Y') }}</h5>
                                        <small class="text-muted">{{ session.start_time.strftime('%H:%M') }} - {{ session.end_time.strftime('%H:%M') }}</small>
                                    </div>
                                    <p class="mb-1">
                                        <strong>Lieu:</strong> {{ session.location or 'À déterminer' }}
                                    </p>
                                    <small class="text-muted">
                                        {% if session.group.participants|length >= session.group.max_participants %}
                                            <span class="text-danger">
                                                <i class="fas fa-exclamation-circle me-1"></i> Complet ({{ session.group.participants|length }}/{{ session.group.max_participants }})
                                            </span>
                                        {% else %}
                                            <span class="text-success">
                                                <i class="fas fa-users me-1"></i> Places disponibles ({{ session.group.participants|length }}/{{ session.group.max_participants }})
                                            </span>
                                        {% endif %}
                                    </small>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="alert alert-info mt-4">
                            <i class="fas fa-info-circle me-2"></i>
                            Aucune session n'est programmée pour cette formation actuellement.
                        </div>
                    {% endif %}
                    
                    <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
                        <a href="{{ url_for('main.propose_time', training_id=training.id) }}" class="btn btn-primary">
                            <i class="fas fa-calendar-plus me-1"></i> Proposer un créneau
                        </a>
                    </div>
                </div>
                <div class="card-footer bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i> 
                            Responsable: {{ training.service.manager_name }} ({{ training.service.manager_email }})
                        </small>
                        <a href="{{ url_for('main.service_details', service_id=training.service.id) }}" class="btn btn-outline-secondary btn-sm">
                            <i class="fas fa-arrow-left me-1"></i> Retour au service
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Documents associés -->
    {% if documents %}
    <div class="row mb-5">
        <div class="col-md-8 mx-auto">
            <div class="card shadow-sm">
                <div class="card-header bg-light">
                    <h2 class="h5 mb-0">Documents associés</h2>
                </div>
                <div class="card-body">
                    <div class="list-group">
                        {% for document in documents %}
                            <div class="list-group-item list-group-item-action">
                                <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">
                                        <i class="fas {{ document.file_type|lower|replace('.', '') }} me-2"></i>
                                        {{ document.name }}
                                    </h5>
                                    <small class="text-muted">{{ document.created_at.strftime('%d/%m/%Y') }}</small>
                                </div>
                                {% if document.description %}
                                    <p class="mb-1">{{ document.description }}</p>
                                {% endif %}
                                <div class="d-flex justify-content-between align-items-center">
                                    <small class="text-muted">{{ document.file_size|filesizeformat }}</small>
                                    <button onclick="downloadDocument('{{ document.id }}', '{{ document.name }}')" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-download me-1"></i> Télécharger
                                    </button>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Modal pour le téléchargement -->
    <div class="modal fade" id="downloadModal" tabindex="-1" aria-labelledby="downloadModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="downloadModalLabel">Télécharger le document</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Vous allez télécharger le document <strong id="documentNameSpan"></strong>.</p>
                    <p>Veuillez entrer votre email pour que nous puissions suivre le téléchargement:</p>
                    <form id="downloadForm">
                        <input type="hidden" id="documentIdInput">
                        <div class="mb-3">
                            <label for="emailInput" class="form-label">Email</label>
                            <input type="email" class="form-control" id="emailInput" required>
                        </div>
                        <div class="mb-3">
                            <label for="nameInput" class="form-label">Nom (optionnel)</label>
                            <input type="text" class="form-control" id="nameInput">
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-download me-1"></i> Télécharger
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}


FICHIER: utils.py
"""
Utilitaires pour le système de réservation Anecoop.
Ce module contient des fonctions utilitaires diverses.
"""

import os
import csv
import io
import pytz
from datetime import datetime, timedelta
from flask import current_app, url_for
from models import (
    Service, Training, Group, Participant, Session, 
    Attendance, TimeProposal, Document, DocumentDownload
)

# Constantes
FRENCH_TIMEZONE = pytz.timezone('Europe/Paris')


def format_datetime(dt, format='%d/%m/%Y %H:%M'):
    """Formate une date et heure pour l'affichage."""
    if dt is None:
        return ''
    
    # Assurer que dt est en UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    # Convertir en heure française
    dt = dt.astimezone(FRENCH_TIMEZONE)
    
    return dt.strftime(format)


def format_date(dt, format='%d/%m/%Y'):
    """Formate une date pour l'affichage."""
    if dt is None:
        return ''
    return format_datetime(dt, format)


def format_time(dt, format='%H:%M'):
    """Formate une heure pour l'affichage."""
    if dt is None:
        return ''
    return format_datetime(dt, format)


def get_status_label(status, entity_type='default'):
    """Retourne un label formaté pour un statut."""
    status_labels = {
        'default': {
            'active': 'Actif',
            'inactive': 'Inactif',
            'scheduled': 'Planifié',
            'completed': 'Terminé',
            'cancelled': 'Annulé',
            'pending': 'En attente',
            'approved': 'Approuvé',
            'rejected': 'Rejeté',
            'registered': 'Inscrit',
            'attended': 'Présent',
            'absent': 'Absent'
        },
        'session': {
            'scheduled': 'Planifiée',
            'completed': 'Terminée',
            'cancelled': 'Annulée'
        },
        'proposal': {
            'pending': 'En attente',
            'approved': 'Approuvée',
            'rejected': 'Rejetée'
        },
        'group': {
            'active': 'Actif',
            'completed': 'Terminé',
            'cancelled': 'Annulé'
        }
    }
    
    entity_labels = status_labels.get(entity_type, status_labels['default'])
    return entity_labels.get(status, status)


def get_status_class(status):
    """Retourne une classe CSS pour un statut."""
    status_classes = {
        'active': 'success',
        'inactive': 'secondary',
        'scheduled': 'primary',
        'completed': 'success',
        'cancelled': 'danger',
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'registered': 'info',
        'attended': 'success',
        'absent': 'danger'
    }
    return status_classes.get(status, 'secondary')


def get_file_icon(file_type):
    """Retourne une icône pour un type de fichier."""
    file_icons = {
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word',
        'docx': 'fa-file-word',
        'xls': 'fa-file-excel',
        'xlsx': 'fa-file-excel',
        'ppt': 'fa-file-powerpoint',
        'pptx': 'fa-file-powerpoint',
        'txt': 'fa-file-alt',
        'zip': 'fa-file-archive'
    }
    return file_icons.get(file_type.lower(), 'fa-file')


def format_file_size(size):
    """Formate une taille de fichier pour l'affichage."""
    if size < 1024:
        return f"{size} octets"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} Mo"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} Go"


def generate_export_csv(items, fields, filename):
    """Génère un fichier CSV d'export."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    
    # Écrire l'en-tête
    writer.writerow(fields.keys())
    
    # Écrire les données
    for item in items:
        row = []
        for field in fields.values():
            if callable(field):
                row.append(field(item))
            elif isinstance(field, str) and hasattr(item, field):
                value = getattr(item, field)
                # Formater les dates
                if isinstance(value, datetime):
                    value = format_datetime(value)
                row.append(value)
            else:
                row.append('')
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue(), filename


def export_participants():
    """Exporte les participants au format CSV."""
    participants = Participant.query.all()
    
    fields = {
        'ID': 'id',
        'Nom': 'name',
        'Email': 'email',
        'Département': 'department',
        'Groupe': lambda p: p.group.name if p.group else '',
        'Service': lambda p: p.group.service.name if p.group else '',
        'Vérifié': lambda p: 'Oui' if p.verified else 'Non',
        'Date de création': 'created_at'
    }
    
    return generate_export_csv(participants, fields, 'participants.csv')


def export_sessions():
    """Exporte les sessions au format CSV."""
    sessions = Session.query.all()
    
    fields = {
        'ID': 'id',
        'Formation': lambda s: s.training.name,
        'Service': lambda s: s.training.service.name,
        'Groupe': lambda s: s.group.name,
        'Date de début': 'start_time',
        'Date de fin': 'end_time',
        'Lieu': 'location',
        'Statut': lambda s: get_status_label(s.status, 'session'),
        'Participants': lambda s: Attendance.query.filter_by(session_id=s.id).count(),
        'Présents': lambda s: Attendance.query.filter_by(session_id=s.id, status='attended').count(),
        'Notes': 'notes'
    }
    
    return generate_export_csv(sessions, fields, 'sessions.csv')


def get_weekly_report_data(start_date=None, end_date=None):
    """Récupère les données pour un rapport hebdomadaire."""
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=7)
    
    if end_date is None:
        end_date = datetime.utcnow()
    
    # Récupérer les nouvelles propositions
    new_proposals = TimeProposal.query.filter(
        TimeProposal.created_at >= start_date,
        TimeProposal.created_at <= end_date
    ).all()
    
    # Récupérer les sessions à venir
    upcoming_sessions = Session.query.filter(
        Session.start_time >= end_date,
        Session.start_time <= end_date + timedelta(days=7),
        Session.status == 'scheduled'
    ).order_by(Session.start_time).all()
    
    # Récupérer les sessions terminées
    completed_sessions = Session.query.filter(
        Session.status == 'completed',
        Session.end_time >= start_date,
        Session.end_time <= end_date
    ).all()
    
    # Récupérer les nouveaux participants
    new_participants = Participant.query.filter(
        Participant.created_at >= start_date,
        Participant.created_at <= end_date
    ).all()
    
    # Calculer le nombre de propositions en attente
    pending_proposals = TimeProposal.query.filter_by(status='pending').all()
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'new_proposals': new_proposals,
        'upcoming_sessions': upcoming_sessions,
        'completed_sessions': completed_sessions,
        'new_participants': new_participants,
        'pending_proposals': pending_proposals
    }


def create_ics_calendar(sessions):
    """Crée un fichier iCalendar pour un ensemble de sessions."""
    from icalendar import Calendar, Event
    
    cal = Calendar()
    cal.add('prodid', '-//Anecoop Formations//anecoop-france.com//')
    cal.add('version', '2.0')
    
    for session in sessions:
        event = Event()
        event.add('summary', session.training.name)
        event.add('dtstart', session.start_time)
        event.add('dtend', session.end_time)
        event.add('location', session.location or 'À déterminer')
        event.add('description', session.training.description or '')
        
        # Ajouter les organisateurs
        organizers = []
        if session.training.service.manager_name:
            organizers.append(session.training.service.manager_name)
        
        if organizers:
            event.add('organizer', ', '.join(organizers))
        
        cal.add_component(event)
    
    return cal.to_ical()


def get_document_stats(document_id):
    """Récupère les statistiques de téléchargement d'un document."""
    downloads = DocumentDownload.query.filter_by(document_id=document_id).all()
    
    stats = {
        'total': len(downloads),
        'unique_users': len(set(d.user_email for d in downloads)),
        'by_date': {}
    }
    
    for download in downloads:
        date_str = format_date(download.downloaded_at)
        if date_str in stats['by_date']:
            stats['by_date'][date_str] += 1
        else:
            stats['by_date'][date_str] = 1
    
    return stats
