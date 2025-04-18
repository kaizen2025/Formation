=== Local GitIngest - Analyse compactée de . ===

Résumé:
Répertoire: .
Fichiers analysés: 36
Tokens estimés (approximatif): 244.4k

Structure des répertoires:
└── Formation/
├── .env
├── GitIngestReport.txt
├── app.log
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
│   ├── services.html
│   ├── track_proposal.html
│   ├── training_details.html
│   ├── trainings.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── edit_training.html
│   │   ├── layout.html
│   │   ├── login.html
│   │   ├── trainings.html
│   │   ├── upload_document.html
│   ├── errors/
│   │   ├── 403.html
│   │   ├── 404.html
│   │   ├── 500.html

Contenu des fichiers (compacté):

FICHIER: .env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=anecoopFormationsBooking2025SecretKey
DATABASE_URL=postgresql://khoiffzx:jagtqaxjqdwxkyxklzjw@alpha.europe.mkdb.sh:5432/wypdrdri
MAIL_SERVER=outlook.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=kbivia@anecoop-france.com
MAIL_PASSWORD=kb3272XM&
MAIL_DEFAULT_SENDER=kbivia@anecoop-france.com
ADMIN_PASSWORD=Anecoop2025
APP_NAME=Anecoop Formations
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max upload size
SESSION_LIFETIME=1440  # 24 heures en minutes
RENDER_EXTERNAL_URL=https://anecoop-formations.onrender.com

FICHIER: app.py
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from config import get_config
from models import db
from routes import register_blueprints
from services import mail, initialize_database, send_weekly_summary_to_admin
application_instance = None
scheduler = None
def setup_logging(app):
    global application_instance, scheduler
    if application_instance is not None:
        return application_instance
    app = Flask(__name__)
    instance_id = str(uuid.uuid4())
    app.config['INSTANCE_ID'] = instance_id
    app.config.from_object(get_config(config_name))
    setup_logging(app)
    logging.info(f"Initialisation de l'application: {app.config['APP_NAME']} - Instance {instance_id}")
    logging.info(f"Mode: {config_name}")
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    init_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    @app.context_processor
    def utility_processor():
        return {
            'app_name': app.config['APP_NAME'],
            'current_year': datetime.utcnow().year,
            'instance_id': instance_id[:8],
            'now': datetime.utcnow(),  # Ajout de la date actuelle pour les templates
            'config': app.config
        }
    with app.app_context():
        try:
            if initialize_database():
                logging.info("Base de données initialisée avec succès")
            else:
                logging.error("Échec de l'initialisation de la base de données")
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
    if scheduler is None:
        scheduler = configure_scheduler(app)
    application_instance = app
    return app
def init_extensions(app):
    @app.errorhandler(404)
    def page_not_found(e):
        logging.warning(f"Page non trouvée: {request.path}")
        return render_template('errors/404.html'), 404
    @app.errorhandler(500)
    def internal_server_error(e):
        logging.error(f"Erreur serveur interne: {str(e)}")
        return render_template('errors/500.html'), 500
    @app.errorhandler(403)
    def forbidden(e):
        logging.warning(f"Accès refusé: {request.path}")
        return render_template('errors/403.html'), 403
    @app.errorhandler(413)
    def request_entity_too_large(e):
        logging.warning(f"Fichier trop volumineux: {request.path}")
        flash("Le fichier téléchargé est trop volumineux. Taille maximale: 16 Mo.", "danger")
        return redirect(request.referrer or url_for('main.index'))
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return jsonify(error="Requête incorrecte", message=str(e)), 400
        return render_template('errors/400.html', error=str(e)), 400
    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith('/api/'):
            return jsonify(error="Non autorisé", message=str(e)), 401
        return render_template('errors/401.html', error=str(e)), 401
def configure_scheduler(app):
    global scheduler
    if scheduler and scheduler.running:
        logging.info("Arrêt du planificateur de tâches")
        scheduler.shutdown()
app = create_app(os.getenv('FLASK_ENV', 'development'))
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"Démarrage du serveur sur le port {port}")
    try:
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=app.config.get('DEBUG', False),
            use_reloader=app.config.get('DEBUG', False)
        )
    except KeyboardInterrupt:
        logging.info("Arrêt du serveur")
    finally:
        shutdown_scheduler()

FICHIER: config.py
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
class Config:
    DEBUG = True
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True
    PREFERRED_URL_SCHEME = 'http'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'True') == 'True'
    CORS_HEADERS = 'Content-Type'
class ProductionConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    PRESERVE_CONTEXT_ON_EXCEPTION = False
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
def get_config(config_name=None):

FICHIER: dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p static/uploads
EXPOSE 8000
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

FICHIER: models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Index, event
import uuid
db = SQLAlchemy()
def generate_uuid():
    __tablename__ = 'services'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    manager_name = db.Column(db.String(100), nullable=False)
    manager_email = db.Column(db.String(100), nullable=False, index=True)
    color = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trainings = db.relationship('Training', backref='service', lazy='select')
    groups = db.relationship('Group', backref='service', lazy='select')
    def __repr__(self):
        return f'<Service {self.name}>'
class Training(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    service_id = db.Column(db.String(50), db.ForeignKey('services.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    min_participants = db.Column(db.Integer, default=8)
    max_participants = db.Column(db.Integer, default=12)
    status = db.Column(db.String(20), default='active', index=True)  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    participants = db.relationship('Participant', backref='group', lazy='select')
    sessions = db.relationship('Session', backref='group', lazy='select')
    def __repr__(self):
        return f'<Group {self.name}>'
    @property
    def is_full(self):
        return len(self.participants) >= self.max_participants
class Participant(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    training_id = db.Column(db.String(50), db.ForeignKey('trainings.id'), nullable=False, index=True)
    group_id = db.Column(db.String(36), db.ForeignKey('groups.id'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='scheduled', index=True)  # scheduled, completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    attendances = db.relationship('Attendance', backref='session', lazy='select')
    proposals = db.relationship('TimeProposal', backref='session', lazy='select')
    def __repr__(self):
        return f'<Session {self.id} - {self.start_time}>'
    __table_args__ = (
        Index('idx_session_training_start_time', training_id, start_time),
        Index('idx_session_status_start_time', status, start_time),
    )
class Attendance(db.Model):
    __tablename__ = 'time_proposals'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=True)
    training_id = db.Column(db.String(50), db.ForeignKey('trainings.id'), nullable=False, index=True)
    proposer_email = db.Column(db.String(100), nullable=False, index=True)
    proposer_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    proposed_time = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    training = db.relationship('Training', back_populates='proposals', lazy='joined')
    def __repr__(self):
        return f'<TimeProposal {self.id} - {self.proposed_time}>'
    __table_args__ = (
        Index('idx_proposal_training_status', training_id, status),
        Index('idx_proposal_status_created', status, created_at),
    )
class Document(db.Model):
    __tablename__ = 'document_downloads'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    user_email = db.Column(db.String(100), nullable=False, index=True)
    user_name = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    def __repr__(self):
        return f'<DocumentDownload {self.id}>'
class AuditLog(db.Model):
    try:
        db.create_all()
        if Service.query.count() == 0:
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
        if Training.query.count() == 0:
            services = Service.query.all()
            training_templates = current_app.config['TRAININGS']
            for service in services:
                for training_data in training_templates:
                    training_id = f"{service.id}-{training_data['id']}"
                    existing = Training.query.filter_by(id=training_id).first()
                    if not existing:
                        training = Training(
                            id=training_id,
                            service_id=service.id,
                            name=training_data['name'],
                            description=training_data['description'],
                            duration=training_data['duration']
                        )
                        db.session.add(training)
                        logger.info(f"Formation créée: {training_id} pour {service.name}")
            db.session.commit()
            logger.info("Formations initialisées avec succès")
@event.listens_for(Session, 'before_insert')
def session_before_insert(mapper, connection, target):
    if target.end_time <= target.start_time:
        raise ValueError("La date de fin doit être après la date de début")

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
Flask>=3.0.3  # Latest stable version, improved async support
Flask-SQLAlchemy>=3.1.1  # Latest, compatible with Flask 3.0
Flask-Migrate>=4.0.7  # Latest, supports SQLAlchemy 2.x
Flask-Mailman>=1.0.0  # Modern replacement for Flask-Mail
psycopg[binary]>=3.2.1  # Modern alternative to psycopg2, better Python 3.13 support
python-dotenv>=1.0.1  # Latest, minor update
Werkzeug>=3.0.3  # Latest, compatible with Flask 3.0
Jinja2>=3.1.4  # Latest, minor update
gunicorn>=22.0.0  # Latest, improved performance
APScheduler>=3.10.5  # Latest, minor update
icalendar>=5.0.13  # Latest, bug fixes
pytz>=2024.2  # Latest, updated timezone data
email-validator>=2.2.0  # Latest, improved validation
pytest>=8.3.3  # Latest, improved features
pytest-flask>=1.3.0  # Latest, compatible with Flask 3.0
python-slugify

FICHIER: routes.py
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
main = Blueprint('main', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')
api = Blueprint('api', __name__, url_prefix='/api')
@main.route('/')
def index():
    services = Service.query.all()
    return render_template('services.html', services=services)
@main.route('/service/<service_id>')
def service_details(service_id):
    services = Service.query.all()
    selected_service_id = request.args.get('service')
    query = Training.query
    if selected_service_id:
        query = query.filter_by(service_id=selected_service_id)
    all_trainings = query.all()
    current_app.logger.info(f"Récupération de {len(all_trainings)} formations" + 
                           (f" pour le service {selected_service_id}" if selected_service_id else ""))
    durations = sorted(list(set([t.duration for t in Training.query.all()])))
    return render_template(
        'trainings.html', 
        trainings=all_trainings, 
        services=services,
        durations=durations,
        selected_service_id=selected_service_id,
        now=datetime.utcnow()
    )
@main.route('/training/<training_id>')
def training_details(training_id):
    training = Training.query.get_or_404(training_id)
    sessions = TrainingSession.query.filter_by(training_id=training_id).order_by(TrainingSession.start_time).all()
    return render_template('training_sessions.html', training=training, sessions=sessions)
@main.route('/training/<training_id>/propose', methods=['GET', 'POST'])
def propose_time(training_id):
    proposal = TimeProposal.query.filter(
        TimeProposal.notes.like(f"%Token de suivi: {token}%")
    ).first_or_404()
    return render_template('track_proposal.html', proposal=proposal)
@main.route('/documents')
def documents():
    document = Document.query.get_or_404(document_id)
    if not document.is_public and 'admin_logged_in' not in session:
        abort(403)
    return render_template('document_details.html', document=document)
@main.route('/document/<document_id>/download')
def download_document(document_id):
    services = Service.query.all()
    start_date = request.args.get('start', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date = request.args.get('end', (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'))
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
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
@admin.route('/login', methods=['GET', 'POST'])
def login():
    logout_admin()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('main.index'))
@admin.route('/')
@login_required
def dashboard():
    services = Service.query.all()
    return render_template('admin/services.html', services=services)
@admin.route('/service/<service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    trainings = Training.query.all()
    services = Service.query.all()
    return render_template('admin/trainings.html', trainings=trainings, services=services)
@admin.route('/training/add', methods=['POST'])
@login_required
def add_training():
    service_id = request.args.get('service_id')
    query = Training.query
    if service_id:
        query = query.filter(Training.service_id == service_id)
    trainings = query.all()
    result = []
    for training in trainings:
        result.append({
            'id': training.id,
            'name': training.name,
            'service_id': training.service_id,
            'service_name': training.service.name,
            'duration': training.duration,
            'description': training.description
        })
    return jsonify(result)
@api.route('/sessions/create', methods=['POST'])
@login_required
def create_session():
    training = Training.query.get_or_404(training_id)
    services = Service.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        service_id = request.form.get('service_id')
        duration = int(request.form.get('duration', 90))
        description = request.form.get('description')
        if not name or not service_id:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('admin/edit_training.html', training=training, services=services)
        service = Service.query.get(service_id)
        if not service:
            flash('Service introuvable.', 'danger')
            return render_template('admin/edit_training.html', training=training, services=services)
        training.name = name
        training.service_id = service_id
        training.duration = duration
        training.description = description
        try:
            db.session.commit()
            flash('Formation mise à jour avec succès.', 'success')
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
    groups = Group.query.all()
    return render_template('admin/groups.html', groups=groups)
@admin.route('/group/<group_id>', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    participants = Participant.query.filter_by(group_id=group_id).all()
    return render_template('admin/group_participants.html', group=group, participants=participants)
@admin.route('/sessions')
@login_required
def manage_sessions():
    session = TrainingSession.query.get_or_404(session_id)
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        location = request.form.get('location')
        status = request.form.get('status')
        notes = request.form.get('notes')
        try:
            date_parts = date_str.split('/')
            date = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            start_time_parts = start_time_str.split(':')
            start_time = date.replace(hour=int(start_time_parts[0]), minute=int(start_time_parts[1]))
            end_time_parts = end_time_str.split(':')
            end_time = date.replace(hour=int(end_time_parts[0]), minute=int(end_time_parts[1]))
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
    document = Document.query.get_or_404(document_id)
    try:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
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
    if send_weekly_summary_to_admin():
        flash('Résumé hebdomadaire envoyé avec succès.', 'success')
    else:
        flash('Erreur lors de l\'envoi du résumé hebdomadaire.', 'danger')
    return redirect(url_for('admin.dashboard'))
@api.route('/sessions')
def get_sessions():
    data = request.json
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.fromisoformat(end_time_str)
    conflicts = TrainingSession.query.filter(
        TrainingSession.start_time < end_time,
        TrainingSession.end_time > start_time
    ).all()
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
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)

FICHIER: services.py
import os
import secrets
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, current_app, request, abort
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from models import (
    db, Service, Training, Group, Participant, Session, 
    Attendance, TimeProposal, Document, DocumentDownload, AuditLog
)
logger = logging.getLogger(__name__)
mail = Mail()
def login_required(f):
    try:
        admin_password = current_app.config['ADMIN_PASSWORD']
        if not admin_password:
            logger.warning("Tentative de connexion administrateur mais aucun mot de passe n'est configuré")
            return False
        if password == admin_password:
            session['admin_logged_in'] = True
            session['login_time'] = datetime.utcnow().isoformat()
            session.permanent = True
            log_audit_event('login', 'admin', 'admin', 'Connexion administrateur')
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else "Unknown"
            logger.info(f"Connexion administrateur réussie depuis {ip_address} avec {user_agent}")
            return True
        ip_address = request.remote_addr
        logger.warning(f"Tentative de connexion administrateur échouée depuis {ip_address}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification: {str(e)}")
        return False
def logout_admin():
    try:
        db.create_all()
        if Service.query.count() == 0:
            logger.info("Initialisation des services...")
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
        if Training.query.count() == 0:
            logger.info("Initialisation des formations...")
            services = Service.query.all()
            if services:
                for training_data in current_app.config['TRAININGS']:
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
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            logger.info(f"Dossier d'uploads créé: {upload_folder}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
        db.session.rollback()
        return False
def send_email(subject, recipients, template, **kwargs):
    if not recipients:
        logger.error("Aucun destinataire fourni pour l'envoi d'email")
        return False
    if isinstance(recipients, str):
        recipients = [recipients]
    try:
        mail_server = current_app.config.get('MAIL_SERVER')
        mail_port = current_app.config.get('MAIL_PORT')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
        if not all([mail_server, mail_port, mail_username, mail_password, mail_sender]):
            logger.error("Configuration email incomplète")
            return False
        msg = MIMEMultipart()
        msg['From'] = mail_sender
        msg['Subject'] = subject
        msg['To'] = ", ".join(recipients)
        kwargs['app_name'] = current_app.config.get('APP_NAME', 'Anecoop Formations')
        kwargs['base_url'] = request.url_root.rstrip('/')
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith('/'):
                if key.endswith('_link') or key.endswith('_url'):
                    kwargs[key] = f"{kwargs['base_url']}{value}"
        html_content = template.format(**kwargs)
        msg.attach(MIMEText(html_content, 'html'))
        try:
            server = smtplib.SMTP(mail_server, mail_port)
            if current_app.config.get('DEBUG', False):
                server.set_debuglevel(1)
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, recipients, msg.as_string())
            server.quit()
            logger.info(f"Email envoyé avec succès à {recipients}")
            return True
        except smtplib.SMTPException as smtp_error:
            logger.error(f"Erreur SMTP lors de l'envoi d'email: {str(smtp_error)}")
            if "Authentication failed" in str(smtp_error):
                logger.info("Tentative avec une méthode d'authentification alternative")
                try:
                    server = smtplib.SMTP(mail_server, mail_port)
                    server.ehlo()
                    if mail_use_tls:
                        server.starttls()
                    server.ehlo()
                    server.login(mail_username, mail_password)
                    server.sendmail(mail_sender, recipients, msg.as_string())
                    server.close()
                    logger.info("Email envoyé avec la méthode alternative")
                    return True
                except Exception as alt_error:
                    logger.error(f"Échec de la méthode alternative: {str(alt_error)}")
            if current_app.config.get('FLASK_ENV') == 'development':
                logger.warning("Mode développement - Simulation d'envoi d'email réussi")
                logger.info(f"À: {recipients}")
                logger.info(f"Sujet: {subject}")
                logger.info(f"Contenu: {html_content[:200]}...")
                return True
            return False
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email: {str(e)}")
        return False
def send_confirmation_email(email, name, training_name, proposed_time, token):
    date_str = proposed_time.strftime("%d/%m/%Y")
    time_str = proposed_time.strftime("%H:%M")
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
    date_str = proposal.proposed_time.strftime("%d/%m/%Y")
    time_str = proposal.proposed_time.strftime("%H:%M")
    location = proposal.session.location if proposal.session else "À déterminer"
    training_link = url_for('main.training_details', training_id=proposal.training_id, _external=True)
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
    date_str = proposal.proposed_time.strftime("%d/%m/%Y")
    time_str = proposal.proposed_time.strftime("%H:%M")
    new_proposal_link = url_for('main.propose_time', training_id=proposal.training_id, _external=True)
    sessions_link = url_for('main.training_details', training_id=proposal.training_id, _external=True)
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
def create_time_proposal(training_id, email, name, department, proposed_time):
    try:
        proposal = TimeProposal.query.get(proposal_id)
        if not proposal:
            return False, "Proposition introuvable"
        if proposal.status != 'pending':
            return False, f"La proposition a déjà été {proposal.status}"
        if session_id:
            session = Session.query.get(session_id)
            if not session:
                return False, "Session introuvable"
        else:
            training = Training.query.get(proposal.training_id)
            if not training:
                return False, "Formation introuvable"
            end_time = proposal.proposed_time + timedelta(minutes=training.duration)
            group = Group.query.filter_by(
                service_id=training.service_id,
                status='active'
            ).order_by(Group.created_at.desc()).first()
            if not group or Group.query.join(Session).filter(
                Group.id == group.id,
                Session.status.in_(['scheduled', 'completed'])
            ).count() >= 4:  # Max 4 sessions par groupe
                group_name = f"Groupe {training.service.name} - {datetime.utcnow().strftime('%B %Y')}"
                group = Group(
                    service_id=training.service_id,
                    name=group_name,
                    status='active'
                )
                db.session.add(group)
                db.session.flush()  # Obtenir l'ID sans commit
            conflicts = Session.query.filter(
                Session.start_time < end_time,
                Session.end_time > proposal.proposed_time,
                Session.status == 'scheduled'
            ).all()
            if conflicts:
                conflict_info = ", ".join([f"{c.training.name} ({c.start_time.strftime('%d/%m/%Y %H:%M')})" for c in conflicts[:3]])
                return False, f"Conflit d'horaire avec d'autres sessions: {conflict_info}"
            session = Session(
                training_id=training.id,
                group_id=group.id,
                start_time=proposal.proposed_time,
                end_time=end_time,
                location=location or "À déterminer",
                status='scheduled'
            )
            db.session.add(session)
        proposal.status = 'approved'
        proposal.session_id = session.id
        db.session.commit()
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
        attendance = Attendance(
            session_id=session.id,
            participant_id=participant.id,
            status='registered'
        )
        db.session.add(attendance)
        db.session.commit()
        send_approval_email(proposal)
        log_audit_event(
            'approve',
            'time_proposal',
            proposal.id,
            f"Proposition approuvée pour {proposal.training.name} par {proposal.proposer_name}"
        )
        return True, session.id
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur de base de données lors de l'approbation d'une proposition: {str(e)}")
        return False, "Erreur de base de données. Veuillez réessayer plus tard."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'approbation d'une proposition: {str(e)}")
        return False, str(e)
def reject_time_proposal(proposal_id, reason=None):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
def save_document(training_id, file, name=None, description=None, is_public=True):
    try:
        document = Document.query.get(document_id)
        if not document:
            return False, "Document introuvable"
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
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur de base de données lors de l'enregistrement d'un téléchargement: {str(e)}")
        return False, "Erreur de base de données. Veuillez réessayer plus tard."
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'enregistrement d'un téléchargement: {str(e)}")
        return False, str(e)
def log_audit_event(action, entity_type, entity_id, description=None):
    try:
        admin_email = current_app.config.get('MAIL_DEFAULT_SENDER')
        if not admin_email:
            logger.error("Aucun email d'administrateur configuré pour l'envoi du résumé hebdomadaire")
            return False
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
        pending_proposals = TimeProposal.query.filter_by(status='pending').count()
        subject = f"Résumé hebdomadaire - {current_app.config.get('APP_NAME', 'Anecoop Formations')}"
        template = """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
                <h2 style="color: #0d6efd;">Résumé hebdomadaire - {app_name}</h2>
            </div>
            <p>Voici le résumé des activités de la semaine du {start_date} au {end_date}:</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Statistiques générales</h3>
                <ul>
                    <li>Nouvelles propositions de créneaux: <strong>{new_proposals}</strong></li>
                    <li>Sessions à venir cette semaine: <strong>{upcoming_sessions}</strong></li>
                    <li>Sessions terminées cette semaine: <strong>{completed_sessions}</strong></li>
                    <li>Nouveaux participants: <strong>{new_participants}</strong></li>
                </ul>
            </div>
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #856404;">Propositions en attente</h3>
                <p>Il y a actuellement <strong>{pending_proposals}</strong> propositions en attente de validation.</p>
            </div>
            <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #0c5460;">Actions recommandées</h3>
                <ul>
                    <li><a href="{pending_link}" style="color: #0d6efd;">Traiter les propositions en attente</a></li>
                    <li><a href="{upcoming_link}" style="color: #0d6efd;">Vérifier les sessions à venir</a></li>
                    <li><a href="{dashboard_link}" style="color: #0d6efd;">Accéder au tableau de bord</a></li>
                </ul>
            </div>
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                <p>Ce message est généré automatiquement par le système de réservation Anecoop.</p>
            </div>
        </body>
        </html>

FICHIER: setup.py
import os
import sys
import subprocess
import shutil
from pathlib import Path
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
def check_env_file():
    if not os.path.exists('.env'):
        print("[INFO] Création du fichier .env...")
        with open('.env', 'w') as f:
            f.write("""# Configuration générale
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=anecoopFormationsBooking2025SecretKey
DATABASE_URL=postgresql://khoiffzx:jagtqaxjqdwxkyxklzjw@alpha.europe.mkdb.sh:5432/wypdrdri
MAIL_SERVER=outlook.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=kbivia@anecoop-france.com
MAIL_PASSWORD=kb3272XM&
MAIL_DEFAULT_SENDER=kbivia@anecoop-france.com
ADMIN_PASSWORD=Anecoop2025
APP_NAME=Anecoop Formations
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max upload size
SESSION_LIFETIME=1440  # 24 heures en minutes

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
{% extends "admin/layout.html" %}
{% block title %}Tableau de bord - Administration {{ app_name }}{% endblock %}
{% block extra_css %}
<style>
    .stat-card {
        border-left: 4px solid;
        transition: transform 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
    }
    .stat-card-primary {
        border-left-color: #4e73df;
    }
    .stat-card-success {
        border-left-color: #1cc88a;
    }
    .stat-card-info {
        border-left-color: #36b9cc;
    }
    .stat-card-warning {
        border-left-color: #f6c23e;
    }
    .stat-icon {
        font-size: 2rem;
        opacity: 0.2;
    }
    .progress-container {
        height: 10px;
        background-color: #eee;
        border-radius: 5px;
        margin-top: 10px;
    }
    .progress-bar {
        height: 100%;
        border-radius: 5px;
    }
    .session-item {
        border-left: 4px solid;
        margin-bottom: 10px;
        transition: all 0.2s;
    }
    .session-item:hover {
        transform: translateX(5px);
    }
    .proposal-item {
        border-left: 4px solid;
        margin-bottom: 10px;
    }
    .chart-container {
        height: 300px;
    }
</style>
{% endblock %}
{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center mb-4">
    <h1 class="h3">Tableau de bord</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <div class="btn-group me-2">
            <a href="{{ url_for('admin.send_summary') }}" class="btn btn-sm btn-outline-primary">
                <i class="fas fa-envelope me-1"></i> Envoyer le résumé
            </a>
        </div>
        <div class="dropdown">
            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-expanded="false">
                <i class="fas fa-download me-1"></i> Exporter
            </button>
            <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                <li><a class="dropdown-item" href="{{ url_for('admin.export_participants') }}">Participants</a></li>
                <li><a class="dropdown-item" href="{{ url_for('admin.export_sessions') }}">Sessions</a></li>
            </ul>
        </div>
    </div>
</div>
<div class="row">
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card shadow h-100 stat-card stat-card-primary">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Participants</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">{{ stats.participants }}</div>
                        <div class="progress-container">
                            <div class="progress-bar bg-primary" style="width: {{ (stats.participants / 100) * 100 if stats.participants > 0 else 0 }}%"></div>
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-users stat-icon text-primary"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card shadow h-100 stat-card stat-card-success">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-success text-uppercase mb-1">Sessions planifiées</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">{{ stats.upcoming_sessions }}</div>
                        <div class="progress-container">
                            <div class="progress-bar bg-success" style="width: {{ (stats.upcoming_sessions / 50) * 100 if stats.upcoming_sessions > 0 else 0 }}%"></div>
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-calendar-alt stat-icon text-success"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card shadow h-100 stat-card stat-card-info">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-info text-uppercase mb-1">Formations</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">{{ stats.trainings }}</div>
                        <div class="progress-container">
                            <div class="progress-bar bg-info" style="width: {{ (stats.trainings / 20) * 100 if stats.trainings > 0 else 0 }}%"></div>
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-graduation-cap stat-icon text-info"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card shadow h-100 stat-card stat-card-warning">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">Propositions en attente</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">{{ stats.pending_proposals }}</div>
                        <div class="progress-container">
                            <div class="progress-bar bg-warning" style="width: {{ (stats.pending_proposals / 10) * 100 if stats.pending_proposals > 0 else 0 }}%"></div>
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-clock stat-icon text-warning"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
<div class="row">
    <div class="col-lg-6">
        <div class="card shadow mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="m-0 font-weight-bold">Sessions à venir</h6>
                <a href="{{ url_for('admin.manage_sessions') }}" class="btn btn-sm btn-primary">
                    Voir toutes
                </a>
            </div>
            <div class="card-body">
                {% if upcoming_sessions %}
                    {% for session in upcoming_sessions %}
                        <div class="session-item p-3 rounded" style="border-left-color: {{ session.training.service.color }};">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h6 class="mb-1">{{ session.training.name }}</h6>
                                    <div class="small text-muted">{{ session.start_time.strftime('%d/%m/%Y %H:%M') }} - {{ session.end_time.strftime('%H:%M') }}</div>
                                </div>
                                <div>
                                    <span class="badge bg-{{ session.status|status_class }}">{{ session.status|status_label('session') }}</span>
                                </div>
                            </div>
                            <div class="mt-2">
                                <div class="small">
                                    <i class="fas fa-map-marker-alt me-1"></i> {{ session.location or "À déterminer" }}
                                </div>
                                <div class="small">
                                    <i class="fas fa-users me-1"></i> {{ session.attendances|length }} participants
                                </div>
                            </div>
                            <div class="mt-2">
                                <a href="{{ url_for('admin.edit_session', session_id=session.id) }}" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-edit me-1"></i> Modifier
                                </a>
                                <a href="{{ url_for('admin.session_attendances', session_id=session.id) }}" class="btn btn-sm btn-outline-secondary">
                                    <i class="fas fa-clipboard-list me-1"></i> Présences
                                </a>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-2"></i>
                        Aucune session n'est planifiée pour le moment.
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
    <div class="col-lg-6">
        <div class="card shadow mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="m-0 font-weight-bold">Propositions en attente</h6>
                <a href="{{ url_for('admin.manage_proposals') }}" class="btn btn-sm btn-primary">
                    Voir toutes
                </a>
            </div>
            <div class="card-body">
                {% if pending_proposals %}
                    {% for proposal in pending_proposals %}
                        <div class="proposal-item p-3 rounded" style="border-left-color: {{ proposal.training.service.color }};">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h6 class="mb-1">{{ proposal.training.name }}</h6>
                                    <div class="small text-muted">{{ proposal.proposed_time.strftime('%d/%m/%Y %H:%M') }}</div>
                                </div>
                                <div>
                                    <span class="badge bg-warning">En attente</span>
                                </div>
                            </div>
                            <div class="mt-2">
                                <div class="small">
                                    <i class="fas fa-user me-1"></i> {{ proposal.proposer_name }}
                                </div>
                                <div class="small">
                                    <i class="fas fa-envelope me-1"></i> {{ proposal.proposer_email }}
                                </div>
                                {% if proposal.department %}
                                    <div class="small">
                                        <i class="fas fa-building me-1"></i> {{ proposal.department }}
                                    </div>
                                {% endif %}
                            </div>
                            <div class="mt-2">
                                <button class="btn btn-sm btn-outline-success" data-bs-toggle="modal" data-bs-target="#approveModal{{ proposal.id }}">
                                    <i class="fas fa-check me-1"></i> Approuver
                                </button>
                                <button class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#rejectModal{{ proposal.id }}">
                                    <i class="fas fa-times me-1"></i> Rejeter
                                </button>
                            </div>
                        </div>
                        <!-- Modal d'approbation -->
                        <div class="modal fade" id="approveModal{{ proposal.id }}" tabindex="-1" aria-labelledby="approveModalLabel{{ proposal.id }}" aria-hidden="true">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <form action="{{ url_for('admin.approve_proposal', proposal_id=proposal.id) }}" method="post">
                                        <div class="modal-header">
                                            <h5 class="modal-title" id="approveModalLabel{{ proposal.id }}">Approuver la proposition</h5>
                                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                        </div>
                                        <div class="modal-body">
                                            <p>Vous êtes sur le point d'approuver cette proposition:</p>
                                            <ul>
                                                <li><strong>Formation:</strong> {{ proposal.training.name }}</li>
                                                <li><strong>Proposée par:</strong> {{ proposal.proposer_name }}</li>
                                                <li><strong>Date:</strong> {{ proposal.proposed_time.strftime('%d/%m/%Y %H:%M') }}</li>
                                            </ul>
                                            <div class="mb-3">
                                                <label for="location{{ proposal.id }}" class="form-label">Lieu de la session</label>
                                                <input type="text" class="form-control" id="location{{ proposal.id }}" name="location" placeholder="Salle de réunion, Teams, etc." required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="session_id{{ proposal.id }}" class="form-label">Session existante (optionnel)</label>
                                                <select class="form-select" id="session_id{{ proposal.id }}" name="session_id">
                                                    <option value="">Créer une nouvelle session</option>
                                                    <!-- Liste des sessions existantes -->
                                                </select>
                                                <div class="form-text">Si sélectionné, le participant sera ajouté à cette session.</div>
                                            </div>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                                            <button type="submit" class="btn btn-success">
                                                <i class="fas fa-check me-1"></i> Approuver
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                        <!-- Modal de rejet -->
                        <div class="modal fade" id="rejectModal{{ proposal.id }}" tabindex="-1" aria-labelledby="rejectModalLabel{{ proposal.id }}" aria-hidden="true">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <form action="{{ url_for('admin.reject_proposal', proposal_id=proposal.id) }}" method="post">
                                        <div class="modal-header">
                                            <h5 class="modal-title" id="rejectModalLabel{{ proposal.id }}">Rejeter la proposition</h5>
                                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                        </div>
                                        <div class="modal-body">
                                            <p>Vous êtes sur le point de rejeter cette proposition:</p>
                                            <ul>
                                                <li><strong>Formation:</strong> {{ proposal.training.name }}</li>
                                                <li><strong>Proposée par:</strong> {{ proposal.proposer_name }}</li>
                                                <li><strong>Date:</strong> {{ proposal.proposed_time.strftime('%d/%m/%Y %H:%M') }}</li>
                                            </ul>
                                            <div class="mb-3">
                                                <label for="reason{{ proposal.id }}" class="form-label">Motif du rejet (optionnel)</label>
                                                <textarea class="form-control" id="reason{{ proposal.id }}" name="reason" rows="3" placeholder="Indiquez la raison du rejet"></textarea>
                                                <div class="form-text">Ce motif sera inclus dans l'email envoyé au demandeur.</div>
                                            </div>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                                            <button type="submit" class="btn btn-danger">
                                                <i class="fas fa-times me-1"></i> Rejeter
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-2"></i>
                        Aucune proposition en attente.
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
<div class="row">
    <div class="col-lg-8">
        <div class="card shadow mb-4">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold">Activité récente</h6>
            </div>
            <div class="card-body">
                <div class="chart-container">
                    <canvas id="activityChart"></canvas>
                </div>
            </div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card shadow mb-4">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold">Répartition par service</h6>
            </div>
            <div class="card-body">
                <div class="chart-container">
                    <canvas id="servicesChart"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Graphique d'activité
        const activityCtx = document.getElementById('activityChart').getContext('2d');
        const activityChart = new Chart(activityCtx, {
            type: 'line',
            data: {
                labels: ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'],
                datasets: [{
                    label: 'Participants',
                    data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 22, 18],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Sessions',
                    data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 8, 6],
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
        // Graphique par service
        const servicesCtx = document.getElementById('servicesChart').getContext('2d');
        const servicesChart = new Chart(servicesCtx, {
            type: 'doughnut',
            data: {
                labels: [
                    'Comptabilité', 
                    'Florensud', 
                    'Commerce', 
                    'Qualité', 
                    'Marketing', 
                    'RH'
                ],
                datasets: [{
                    data: [
                        {{ service_stats[0].sessions if service_stats|length > 0 else 0 }},
                        {{ service_stats[1].sessions if service_stats|length > 1 else 0 }},
                        {{ service_stats[2].sessions if service_stats|length > 2 else 0 }},
                        {{ service_stats[3].sessions if service_stats|length > 3 else 0 }},
                        {{ service_stats[4].sessions if service_stats|length > 4 else 0 }},
                        {{ service_stats[5].sessions if service_stats|length > 5 else 0 }}
                    ],
                    backgroundColor: [
                        '#4285F4',
                        '#34A853',
                        '#FBBC05',
                        '#EA4335',
                        '#9C27B0',
                        '#FF9800'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
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
	<script>
    // Vérifier que la session admin est active
    document.addEventListener('DOMContentLoaded', function() {
        // Ajouter une classe pour identifier les pages admin
        document.body.classList.add('admin-page');
        // Vérifier si un élément indiquant une erreur d'authentification est présent
        const sessionExpired = document.querySelector('.session-expired');
        if (sessionExpired) {
            // Rediriger vers la page de connexion
            window.location.href = "{{ url_for('admin.login') }}";
        }
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

FICHIER: templates\admin\upload_document.html
{% extends "admin/layout.html" %}
{% block title %}Télécharger un document - Administration {{ app_name }}{% endblock %}
{% block content %}
<div class="row mb-4">
    <div class="col">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{{ url_for('admin.dashboard') }}">Tableau de bord</a></li>
                <li class="breadcrumb-item"><a href="{{ url_for('admin.manage_documents') }}">Documents</a></li>
                <li class="breadcrumb-item active" aria-current="page">Télécharger un document</li>
            </ol>
        </nav>
        <h1 class="h3">Télécharger un document</h1>
        <p class="text-muted">Ajoutez un nouveau document à une formation.</p>
    </div>
</div>
<div class="row">
    <div class="col-lg-8">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Informations du document</h5>
            </div>
            <div class="card-body">
                <form action="{{ url_for('admin.upload_document') }}" method="post" enctype="multipart/form-data" class="needs-validation" novalidate>
                    <div class="row g-3">
                        <div class="col-md-12">
                            <label for="training_id" class="form-label">Formation <span class="text-danger">*</span></label>
                            <select class="form-select" id="training_id" name="training_id" required>
                                <option value="" {% if not preselect_training_id %}selected{% endif %} disabled>Choisir une formation...</option>
                                {% for training in trainings %}
                                    <option value="{{ training.id }}" {% if preselect_training_id == training.id %}selected{% endif %}>
                                        {{ training.name }} ({{ training.service.name }})
                                    </option>
                                {% endfor %}
                            </select>
                            <div class="invalid-feedback">
                                Veuillez sélectionner une formation.
                            </div>
                        </div>
                        <div class="col-md-12">
                            <label for="name" class="form-label">Nom du document <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="name" name="name" required>
                            <div class="invalid-feedback">
                                Veuillez entrer un nom pour le document.
                            </div>
                            <div class="form-text">Si laissé vide, le nom du fichier sera utilisé.</div>
                        </div>
                        <div class="col-md-12">
                            <label for="description" class="form-label">Description</label>
                            <textarea class="form-control" id="description" name="description" rows="3"></textarea>
                            <div class="form-text">Une brève description du contenu du document.</div>
                        </div>
                        <div class="col-md-12">
                            <label for="file" class="form-label">Fichier <span class="text-danger">*</span></label>
                            <input type="file" class="form-control" id="file" name="file" required onchange="checkFileSize(this, 'file-size-info')">
                            <div class="invalid-feedback">
                                Veuillez sélectionner un fichier.
                            </div>
                            <div id="file-size-info" class="form-text"></div>
                            <div class="form-text">
                                Types de fichiers autorisés: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, ZIP
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="is_public" name="is_public" checked>
                                <label class="form-check-label" for="is_public">
                                    Document public
                                </label>
                                <div class="form-text">
                                    Si coché, le document sera visible par tous les utilisateurs. Sinon, seuls les administrateurs pourront y accéder.
                                </div>
                            </div>
                        </div>
                        <div class="col-12 mt-4">
                            <div class="d-flex justify-content-between">
                                <a href="{{ url_for('admin.manage_documents') }}" class="btn btn-secondary">Annuler</a>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-upload me-1"></i> Télécharger
                                </button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <div class="col-lg-4">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Aperçu</h5>
            </div>
            <div class="card-body text-center">
                <div id="preview-container">
                    <div class="mb-3">
                        <i id="preview-icon" class="fas fa-file fa-4x text-secondary"></i>
                    </div>
                    <h5 id="preview-name">Nom du document</h5>
                    <p id="preview-description" class="text-muted">Description du document</p>
                </div>
            </div>
        </div>
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="card-title mb-0">Information</h5>
            </div>
            <div class="card-body">
                <p class="mb-0">
                    Les documents téléchargés seront stockés dans le dossier configuré et accessibles aux utilisateurs selon les paramètres définis.
                </p>
                <hr>
                <p class="mb-0">
                    <i class="fas fa-info-circle me-1 text-primary"></i>
                    La taille maximale des fichiers est de {{ (config.MAX_CONTENT_LENGTH / 1024 / 1024)|round(0, 'floor') }} Mo.
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Prévisualisation dynamique
        const nameInput = document.getElementById('name');
        const descriptionInput = document.getElementById('description');
        const fileInput = document.getElementById('file');
        const previewName = document.getElementById('preview-name');
        const previewDescription = document.getElementById('preview-description');
        const previewIcon = document.getElementById('preview-icon');
        nameInput.addEventListener('input', function() {
            previewName.textContent = this.value || 'Nom du document';
        });
        descriptionInput.addEventListener('input', function() {
            previewDescription.textContent = this.value || 'Description du document';
        });
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                // Mettre à jour le nom s'il est vide
                if (!nameInput.value) {
                    nameInput.value = fileName;
                    previewName.textContent = fileName;
                }
                // Mettre à jour l'icône selon l'extension
                const extension = fileName.split('.').pop().toLowerCase();
                let iconClass = 'fas fa-file';
                switch(extension) {
                    case 'pdf':
                        iconClass = 'fas fa-file-pdf text-danger';
                        break;
                    case 'doc':
                    case 'docx':
                        iconClass = 'fas fa-file-word text-primary';
                        break;
                    case 'ppt':
                    case 'pptx':
                        iconClass = 'fas fa-file-powerpoint text-warning';
                        break;
                    case 'xls':
                    case 'xlsx':
                        iconClass = 'fas fa-file-excel text-success';
                        break;
                    case 'txt':
                        iconClass = 'fas fa-file-alt text-secondary';
                        break;
                    case 'zip':
                        iconClass = 'fas fa-file-archive text-info';
                        break;
                }
                previewIcon.className = iconClass;
            }
        });
        // Validation du formulaire
        const form = document.querySelector('.needs-validation');
        form.addEventListener('submit', function(event) {
            if (!this.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
    // Fonction pour vérifier la taille du fichier
    function checkFileSize(input, infoId) {
        const maxSize = {{ config.MAX_CONTENT_LENGTH }};
        const infoElement = document.getElementById(infoId);
        if (input.files && input.files[0]) {
            const fileSize = input.files[0].size;
            const fileSizeMB = (fileSize / 1024 / 1024).toFixed(2);
            const maxSizeMB = (maxSize / 1024 / 1024).toFixed(0);
            if (fileSize > maxSize) {
                infoElement.innerHTML = `<span class="text-danger">Fichier trop volumineux: ${fileSizeMB} Mo (max: ${maxSizeMB} Mo)</span>`;
                input.value = ''; // Vider l'input
                return false;
            } else {
                infoElement.innerHTML = `<span class="text-success">Taille du fichier: ${fileSizeMB} Mo</span>`;
                return true;
            }
        } else {
            infoElement.innerHTML = '';
            return false;
        }
    }
</script>
{% endblock %}

FICHIER: templates\calendar.html
{% extends "layout.html" %}
{% block title %}Calendrier des formations - {{ app_name }}{% endblock %}
{% block extra_css %}
<link href='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.10.0/main.min.css' rel='stylesheet' />
<style>
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px;
    }
    .fc-event {
        cursor: pointer;
        border: none !important;
    }
    .calendar-loading {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 10;
    }
    .filter-container {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 20px;
        margin-bottom: 20px;
    }
    /* Styles pour les events du calendrier par service */
    .event-comptabilite { background-color: #4285F4 !important; border-color: #4285F4 !important; }
    .event-florensud { background-color: #34A853 !important; border-color: #34A853 !important; }
    .event-commerce { background-color: #FBBC05 !important; border-color: #FBBC05 !important; }
    .event-qualite { background-color: #EA4335 !important; border-color: #EA4335 !important; }
    .event-marketing { background-color: #9C27B0 !important; border-color: #9C27B0 !important; }
    .event-rh { background-color: #FF9800 !important; border-color: #FF9800 !important; }
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
                            <div class="col-md-6">
                                <label for="filter-service" class="form-label">Filtrer par service</label>
                                <select id="filter-service" class="form-select">
                                    <option value="">Tous les services</option>
                                    {% for service in services %}
                                        <option value="{{ service.id }}">{{ service.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label for="filter-training" class="form-label">Formation</label>
                                <select id="filter-training" class="form-select">
                                    <option value="">Toutes les formations</option>
                                    <!-- Sera rempli dynamiquement par JavaScript -->
                                </select>
                            </div>
                        </div>
                    </div>
                    <div id="calendar-container" class="position-relative">
                        <div id="calendar"></div>
                        <div id="loading" class="calendar-loading d-none">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Chargement...</span>
                            </div>
                        </div>
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
                <a href="#" class="btn btn-primary" id="proposeTimeLink">Proposer un créneau</a>
                <a href="#" class="btn btn-success" id="viewTrainingLink">Voir la formation</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script src='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.10.0/main.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/fullcalendar/5.10.0/locales/fr.min.js'></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Éléments du DOM
        const calendarEl = document.getElementById('calendar');
        const loadingEl = document.getElementById('loading');
        const filterService = document.getElementById('filter-service');
        const filterTraining = document.getElementById('filter-training');
        // Configuration du calendrier
        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,listMonth'
            },
            locale: 'fr',
            buttonText: {
                today: "Aujourd'hui",
                month: 'Mois',
                week: 'Semaine',
                list: 'Liste'
            },
            firstDay: 1, // Lundi comme premier jour
            navLinks: true,
            businessHours: {
                daysOfWeek: [1, 2, 3, 4, 5], // Lundi - Vendredi
                startTime: '09:00',
                endTime: '18:00',
            },
            events: '/api/sessions',
            eventTimeFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            },
            eventClick: function(info) {
                showEventDetails(info.event);
            },
            loading: function(isLoading) {
                if (isLoading) {
                    loadingEl.classList.remove('d-none');
                } else {
                    loadingEl.classList.add('d-none');
                }
            },
            // Personnalisation des événements
            eventClassNames: function(arg) {
                const serviceId = arg.event.extendedProps.serviceId;
                return ['event-' + serviceId];
            },
            eventContent: function(arg) {
                const timeText = arg.timeText;
                const title = arg.event.title;
                return {
                    html: `<div class="fc-content">
                             <div class="fc-time">${timeText}</div>
                             <div class="fc-title">${title}</div>
                           </div>`
                };
            }
        });
        // Initialiser le calendrier
        calendar.render();
        // Fonction pour afficher les détails d'un événement
        function showEventDetails(event) {
            const modal = new bootstrap.Modal(document.getElementById('eventDetailsModal'));
            const modalBody = document.getElementById('eventDetailsBody');
            const proposeTimeLink = document.getElementById('proposeTimeLink');
            const viewTrainingLink = document.getElementById('viewTrainingLink');
            // Récupérer les données de l'événement
            const title = event.title;
            const start = event.start ? new Date(event.start) : null;
            const end = event.end ? new Date(event.end) : null;
            const location = event.extendedProps.location || 'À déterminer';
            const description = event.extendedProps.description || 'Aucune description disponible';
            const serviceName = event.extendedProps.serviceName || '';
            const trainingId = event.extendedProps.trainingId || '';
            // Formater les dates
            const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            const timeOptions = { hour: '2-digit', minute: '2-digit' };
            const formattedDate = start ? start.toLocaleDateString('fr-FR', dateOptions) : '';
            const formattedStartTime = start ? start.toLocaleTimeString('fr-FR', timeOptions) : '';
            const formattedEndTime = end ? end.toLocaleTimeString('fr-FR', timeOptions) : '';
            // Mettre à jour le contenu du modal
            modalBody.innerHTML = `
                <div class="mb-3">
                    <h5>${title}</h5>
                    <p class="text-muted">${description}</p>
                </div>
                <div class="mb-2">
                    <i class="fas fa-building me-2"></i> <strong>Service:</strong> ${serviceName}
                </div>
                <div class="mb-2">
                    <i class="fas fa-calendar-day me-2"></i> <strong>Date:</strong> ${formattedDate}
                </div>
                <div class="mb-2">
                    <i class="fas fa-clock me-2"></i> <strong>Horaires:</strong> ${formattedStartTime} - ${formattedEndTime}
                </div>
                <div class="mb-2">
                    <i class="fas fa-map-marker-alt me-2"></i> <strong>Lieu:</strong> ${location}
                </div>
            `;
            // Mettre à jour les liens
            proposeTimeLink.href = `/training/${trainingId}/propose`;
            viewTrainingLink.href = `/training/${trainingId}`;
            // Afficher le modal
            modal.show();
        }
        // Filtrage du calendrier
        filterService.addEventListener('change', function() {
            const serviceId = this.value;
            // Mettre à jour le filtre des formations
            updateTrainingFilter(serviceId);
            // Appliquer le filtre au calendrier
            filterCalendar();
        });
        filterTraining.addEventListener('change', function() {
            // Appliquer le filtre au calendrier
            filterCalendar();
        });
        // Fonction pour mettre à jour le filtre des formations
        function updateTrainingFilter(serviceId) {
            // Vider le filtre des formations
            filterTraining.innerHTML = '<option value="">Toutes les formations</option>';
            if (!serviceId) {
                return;
            }
            // Afficher le chargement
            loadingEl.classList.remove('d-none');
            // Récupérer les formations du service
            fetch(`/api/trainings?service_id=${serviceId}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(training => {
                        const option = document.createElement('option');
                        option.value = training.id;
                        option.textContent = training.name;
                        filterTraining.appendChild(option);
                    });
                    // Masquer le chargement
                    loadingEl.classList.add('d-none');
                })
                .catch(error => {
                    console.error('Erreur lors de la récupération des formations:', error);
                    loadingEl.classList.add('d-none');
                });
        }
        // Fonction pour filtrer le calendrier
        function filterCalendar() {
            const serviceId = filterService.value;
            const trainingId = filterTraining.value;
            // Récupérer tous les événements
            const events = calendar.getEvents();
            events.forEach(event => {
                let visible = true;
                if (serviceId && event.extendedProps.serviceId !== serviceId) {
                    visible = false;
                }
                if (trainingId && event.extendedProps.trainingId !== trainingId) {
                    visible = false;
                }
                // Mettre à jour la visibilité
                event.setProp('display', visible ? 'auto' : 'none');
            });
        }
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
        height: 100%;
    }
    .document-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .document-icon {
        font-size: 3rem;
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
    .empty-state {
        text-align: center;
        padding: 60px 20px;
    }
    .empty-icon {
        font-size: 5rem;
        color: #d3d3d3;
        margin-bottom: 20px;
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
                            <option value="doc,docx">Word</option>
                            <option value="ppt,pptx">PowerPoint</option>
                            <option value="xls,xlsx">Excel</option>
                            <option value="txt">Texte</option>
                            <option value="zip">Archive</option>
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
                                        {% elif document.file_type == 'txt' %}
                                            <i class="fas fa-file-alt text-secondary"></i>
                                        {% elif document.file_type == 'zip' %}
                                            <i class="fas fa-file-archive text-info"></i>
                                        {% else %}
                                            <i class="fas fa-file text-secondary"></i>
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
                <div class="empty-state">
                    <div class="empty-icon">
                        <i class="fas fa-file-upload"></i>
                    </div>
                    <h4>Aucun document disponible</h4>
                    <p class="text-muted">Les documents des formations seront disponibles ici une fois ajoutés par les administrateurs.</p>
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
                let visibleCount = 0;
                documents.forEach(document => {
                    let showDocument = true;
                    if (serviceValue && document.getAttribute('data-service') !== serviceValue) {
                        showDocument = false;
                    }
                    if (trainingValue && document.getAttribute('data-training') !== trainingValue) {
                        showDocument = false;
                    }
                    if (typeValue) {
                        const docType = document.getAttribute('data-type');
                        const typeValues = typeValue.split(',');
                        if (!typeValues.includes(docType)) {
                            showDocument = false;
                        }
                    }
                    document.style.display = showDocument ? '' : 'none';
                    if (showDocument) visibleCount++;
                });
                // Afficher un message si aucun document trouvé
                let emptyState = documentsContainer.querySelector('.empty-state-filter');
                if (visibleCount === 0) {
                    if (!emptyState) {
                        emptyState = document.createElement('div');
                        emptyState.className = 'empty-state empty-state-filter col-12';
                        emptyState.innerHTML = `
                            <div class="empty-icon">
                                <i class="fas fa-search"></i>
                            </div>
                            <h4>Aucun document correspondant</h4>
                            <p class="text-muted">Modifiez vos critères de recherche pour trouver les documents.</p>
                        `;
                        documentsContainer.appendChild(emptyState);
                    }
                } else if (emptyState) {
                    emptyState.remove();
                }
            };
            serviceFilter.addEventListener('change', filterDocuments);
            trainingFilter.addEventListener('change', filterDocuments);
            typeFilter.addEventListener('change', filterDocuments);
            // Filtrage des formations par service
            serviceFilter.addEventListener('change', function() {
                const serviceId = this.value;
                // Réinitialiser le filtre des formations
                trainingFilter.innerHTML = '<option value="">Toutes les formations</option>';
                if (!serviceId) {
                    // Si aucun service sélectionné, afficher toutes les formations
                    {% for training in trainings %}
                    const option = document.createElement('option');
                    option.value = "{{ training.id }}";
                    option.textContent = "{{ training.name }}";
                    trainingFilter.appendChild(option);
                    {% endfor %}
                    return;
                }
                // Filtrer les formations par service
                {% for training in trainings %}
                if ("{{ training.service_id }}" === serviceId) {
                    const option = document.createElement('option');
                    option.value = "{{ training.id }}";
                    option.textContent = "{{ training.name }}";
                    trainingFilter.appendChild(option);
                }
                {% endfor %}
            });
        }
    });
    // Fonction pour télécharger un document
    function downloadDocument(id, name) {
        // Mettre à jour le modal
        document.getElementById('documentNameSpan').textContent = name;
        document.getElementById('documentIdInput').value = id;
        // Afficher le modal
        const modal = new bootstrap.Modal(document.getElementById('downloadModal'));
        modal.show();
        // Gérer la soumission du formulaire
        document.getElementById('downloadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('emailInput').value;
            const userName = document.getElementById('nameInput').value || '';
            // Rediriger vers l'URL de téléchargement avec les paramètres
            window.location.href = `/document/${id}/download?email=${encodeURIComponent(email)}&name=${encodeURIComponent(userName)}`;
            // Fermer le modal
            modal.hide();
        });
    }
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

FICHIER: templates\services.html
{% extends "layout.html" %}
{% block title %}Services - {{ app_name }}{% endblock %}
{% block content %}
<div class="container">
    <div class="row mb-4">
        <div class="col-md-8 mx-auto">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{{ url_for('main.index') }}">Accueil</a></li>
                    <li class="breadcrumb-item active" aria-current="page">Services</li>
                </ol>
            </nav>
        </div>
    </div>
    <div class="row mb-5">
        <div class="col-lg-10 mx-auto">
            <h1 class="h3 mb-4">Nos services</h1>
            <div class="row row-cols-1 row-cols-md-3 g-4">
                {% for service in services %}
                <div class="col">
                    <div class="card h-100 shadow-sm">
                        <div class="card-header" style="background-color: {{ service.color }}; height: 8px;"></div>
                        <div class="card-body">
                            <h3 class="card-title h5">{{ service.name }}</h3>
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
        </div>
    </div>
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <div class="card border-primary mb-5">
                <div class="card-body text-center">
                    <h3 class="card-title">Vous cherchez une formation spécifique ?</h3>
                    <p class="card-text">Consultez la liste complète des formations disponibles.</p>
                    <a href="{{ url_for('main.trainings') }}" class="btn btn-primary">Voir toutes les formations</a>
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

FICHIER: templates\trainings.html
{% extends "layout.html" %}
{% block title %}Formations - {{ app_name }}{% endblock %}
{% block extra_css %}
<style>
    .training-card {
        transition: all 0.3s ease;
        height: 100%;
        border-radius: 0.5rem;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: none;
        position: relative;
    }
    .training-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0,0,0,0.15);
    }
    .service-badge {
        position: absolute;
        top: 0;
        left: 0;
        width: 5px;
        height: 100%;
    }
    .service-pill {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 50rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .filter-container {
        background-color: #f8f9fa;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .duration-badge {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background-color: rgba(0,0,0,0.6);
        color: white;
        padding: 0.25rem 0.6rem;
        border-radius: 50rem;
        font-size: 0.75rem;
    }
    .training-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #6c757d;
    }
    .empty-state {
        text-align: center;
        padding: 3rem;
        background-color: #f8f9fa;
        border-radius: 0.75rem;
    }
    .empty-icon {
        font-size: 4rem;
        color: #dee2e6;
        margin-bottom: 1rem;
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
                    <li class="breadcrumb-item active" aria-current="page">Formations</li>
                </ol>
            </nav>
        </div>
    </div>
    <div class="row mb-4">
        <div class="col-lg-10 mx-auto">
            <h1 class="h3">Toutes les formations disponibles</h1>
        </div>
    </div>
    <div class="row mb-4">
        <div class="col-lg-10 mx-auto">
            <div class="filter-container">
                <h5 class="mb-3">Filtrer les formations</h5>
                <form method="get" action="{{ url_for('main.trainings') }}" id="filter-form">
                    <div class="row">
                        <div class="col-md-6 mb-3 mb-md-0">
                            <label for="service" class="form-label">Service</label>
                            <select id="service" name="service" class="form-select" onchange="this.form.submit()">
                                <option value="">Tous les services</option>
                                {% for service in services %}
                                    <option value="{{ service.id }}" {% if selected_service_id == service.id %}selected{% endif %}>
                                        {{ service.name }}
                                    </option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="duration" class="form-label">Durée</label>
                            <select id="duration" name="duration" class="form-select" onchange="this.form.submit()">
                                <option value="">Toutes les durées</option>
                                {% for duration in durations %}
                                    <option value="{{ duration }}">
                                        {{ duration // 60 }}h{{ '30' if duration % 60 > 0 else '00' }}
                                    </option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <div class="row mb-5">
        <div class="col-lg-10 mx-auto">
            <div id="trainings-container" class="row g-4">
                {% if trainings %}
                    {% for training in trainings %}
                        <div class="col-lg-4 col-md-6 mb-4">
                            <div class="card training-card">
                                <div class="service-badge" style="background-color: {{ training.service.color }};"></div>
                                <div class="card-body">
                                    <span class="service-pill" style="background-color: {{ training.service.color }}; color: white;">
                                        {{ training.service.name }}
                                    </span>
                                    <div class="duration-badge">
                                        <i class="far fa-clock me-1"></i> {{ training.duration // 60 }}h{{ '30' if training.duration % 60 > 0 else '00' }}
                                    </div>
                                    <div class="training-icon">
                                        {% if 'Teams' in training.name %}
                                            <i class="fas fa-users"></i>
                                        {% elif 'SharePoint' in training.name %}
                                            <i class="fas fa-file-alt"></i>
                                        {% elif 'tâches' in training.name %}
                                            <i class="fas fa-tasks"></i>
                                        {% elif 'fichiers' in training.name %}
                                            <i class="fas fa-folder"></i>
                                        {% else %}
                                            <i class="fas fa-graduation-cap"></i>
                                        {% endif %}
                                    </div>
                                    <h5 class="card-title">{{ training.name }}</h5>
                                    <p class="card-text text-muted">{{ training.description }}</p>
                                    <a href="{{ url_for('main.training_details', training_id=training.id) }}" class="btn btn-outline-primary w-100">
                                        Voir les détails
                                    </a>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="col-12">
                        <div class="empty-state">
                            <div class="empty-icon">
                                <i class="fas fa-search"></i>
                            </div>
                            <h4>Aucune formation ne correspond à vos critères</h4>
                            <p class="text-muted">Essayez de modifier vos filtres ou de réinitialiser la recherche.</p>
                            <a href="{{ url_for('main.trainings') }}" class="btn btn-primary mt-3">
                                <i class="fas fa-undo-alt me-1"></i> Effacer les filtres
                            </a>
                        </div>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

FICHIER: utils.py
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
FRENCH_TIMEZONE = pytz.timezone('Europe/Paris')
def format_datetime(dt, format='%d/%m/%Y %H:%M'):
    if dt is None:
        return ''
    return format_datetime(dt, format)
def format_time(dt, format='%H:%M'):
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
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(fields.keys())
    for item in items:
        row = []
        for field in fields.values():
            if callable(field):
                row.append(field(item))
            elif isinstance(field, str) and hasattr(item, field):
                value = getattr(item, field)
                if isinstance(value, datetime):
                    value = format_datetime(value)
                row.append(value)
            else:
                row.append('')
        writer.writerow(row)
    output.seek(0)
    return output.getvalue(), filename
def export_participants():
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
        organizers = []
        if session.training.service.manager_name:
            organizers.append(session.training.service.manager_name)
        if organizers:
            event.add('organizer', ', '.join(organizers))
        cal.add_component(event)
    return cal.to_ical()
def get_document_stats(document_id):
