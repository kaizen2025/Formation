import os
import json
import logging
import calendar
import datetime
import tempfile
import sys
from typing import Dict, List, Any, Tuple, Optional
from functools import wraps
from urllib.parse import urljoin
from markupsafe import escape

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    session, flash, send_file, abort, g
)
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user # Import Flask-Login
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import psycopg2 # Pour psycopg2.Binary
import psycopg2.extras
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature # Pour les tokens

# Import config (fichier modifié)
from config import (
    DATABASE_URL, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
    EMAIL_CONFIG, ADMIN_PASSWORD_HASH, ADMIN_USERNAME, APP_NAME, CDN_CONFIG,
    SYSTEM_CONFIG, ALLOWED_EXTENSIONS, CALENDAR_CONFIG, DEBUG, APP_VERSION
)
# Import db_manager instance (fichier modifié)
try:
    from db_manager import db_manager
    if db_manager is None:
        raise ImportError("db_manager failed to initialize.")
except (ImportError, ConnectionError) as e:
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"Failed to import or initialize db_manager: {e}. Application cannot start properly.")
    db_manager = None

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24)) # ESSENTIEL pour session/login/csrf
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(seconds=SYSTEM_CONFIG.get('session_timeout', 3600))

# Config Dossier Uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), SYSTEM_CONFIG.get('temp_folder', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = SYSTEM_CONFIG.get('max_upload_size', 10 * 1024 * 1024)

# Config Email
app.config['MAIL_SERVER'] = EMAIL_CONFIG['smtp_server']
app.config['MAIL_PORT'] = EMAIL_CONFIG['smtp_port']
app.config['MAIL_USERNAME'] = EMAIL_CONFIG['username']
app.config['MAIL_PASSWORD'] = EMAIL_CONFIG['password']
app.config['MAIL_USE_TLS'] = EMAIL_CONFIG['use_tls']
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# CSRF Protection
csrf = CSRFProtect(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' # Route de redirection si non loggué
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"

# Token Serializer (pour liens sécurisés)
ts = URLSafeTimedSerializer(app.secret_key)

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, SYSTEM_CONFIG.get('log_level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Modèle Utilisateur Admin pour Flask-Login ---
# (Simplifié ici, pourrait être dans un fichier models.py séparé)
class AdminUser:
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_active = True # Tous les admins sont actifs

    def is_authenticated(self):
        return True # Si l'objet existe, il est authentifié

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id) # Doit retourner une string

    def check_password(self, password):
         return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    """Charge l'utilisateur admin depuis la DB pour Flask-Login."""
    if db_manager:
        user_data = db_manager.get_admin_user_by_id(int(user_id))
        if user_data:
            return AdminUser(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

# --- Décorateurs ---
# login_required est fourni par Flask-Login
# def login_required(f): <-- Supprimer l'ancienne version

def check_db_connection(f):
    """Decorator to check if db_manager is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if db_manager is None:
            logger.critical("Database manager is not available.")
            flash("Erreur critique: Connexion DB impossible. Contactez l'administrateur.", "error")
            # Peut-être rendre une page d'erreur statique ici
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Fonctions Utilitaires (adaptées) ---
def allowed_file(filename):
    """Vérifie si le type de fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_request_ip():
    """Get user IP address from request."""
    # (Code inchangé)
    if request.headers.getlist("X-Forwarded-For"):
       ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.remote_addr:
       ip = request.remote_addr
    else:
        ip = "Unknown"
    return ip

def add_activity_log_wrapper(action: str, user_info: Optional[Dict]=None, details: Optional[Dict]=None, entity_type: Optional[str]=None, entity_id: Optional[int]=None):
     """ Wrapper pour ajouter un log d'activité facilement """
     if db_manager:
          # Enrichir user_info si possible
          log_user_info = {}
          if current_user.is_authenticated:
              log_user_info = {'admin_id': current_user.id, 'username': current_user.username}
          elif user_info: # Passer des infos si pas d'admin loggué (ex: user email)
              log_user_info = user_info

          db_manager.add_activity_log(
              action=action,
              user_info=log_user_info,
              details=details,
              entity_type=entity_type,
              entity_id=entity_id,
              ip_address=get_request_ip(),
              user_agent=request.user_agent.string if request else None
          )

# --- Context Processors and Template Filters (adaptés) ---
@app.context_processor
def inject_template_globals():
    """Injecter des variables globales dans tous les templates"""
    # Récupérer les départements et modules depuis la DB
    departments_list = []
    modules_list = []
    if db_manager:
        try:
            departments_list = db_manager.get_all_departments()
            modules_list = db_manager.get_all_modules(active_only=True)
        except Exception as e:
             logger.warning(f"Contexte: Erreur récupération départements/modules: {e}")

    return {
        'app_name': APP_NAME,
        'app_version': APP_VERSION,
        'current_year': datetime.datetime.now().year,
        'cdn': CDN_CONFIG,
        'departments': departments_list, # Remplacer par données DB
        'formation_modules': modules_list, # Remplacer par données DB
        'is_admin': current_user.is_authenticated, # Utiliser Flask-Login
        'json_dumps': json.dumps # Pour passer des données JS
    }

# --- Importer les filtres depuis utils.py ---
try:
    from utils import format_date_filter, format_datetime_filter, filesizeformat_filter, nl2br_filter
    app.jinja_env.filters['format_date'] = format_date_filter
    app.jinja_env.filters['format_datetime'] = format_datetime_filter
    app.jinja_env.filters['filesizeformat'] = filesizeformat_filter
    app.jinja_env.filters['nl2br'] = nl2br_filter
except ImportError:
    logger.error("Impossible d'importer les filtres depuis utils.py")
    # Définir des fallbacks si nécessaire
    pass


# --- Error Handling (inchangé mais vérifier les templates) ---
@app.errorhandler(404)
# ... (code 404 inchangé)
@app.errorhandler(500)
# ... (code 500 inchangé)
@app.errorhandler(403)
# ... (code 403 inchangé)
@app.errorhandler(413)
# ... (code 413 inchangé, s'assurer que errors/413.html existe)
@app.errorhandler(CSRFError)
# ... (code CSRF inchangé, s'assurer que errors/csrf_error.html existe)


# --- Flux de Réservation (Routes Refactorisées) ---

# Étape 1: Sélection du Groupe/Département
@app.route('/', methods=['GET', 'POST'])
@check_db_connection
def index():
    """Page d'accueil - Étape 1: Sélection du groupe de formation"""
    # Utiliser WTForms pour la validation
    from forms import SelectGroupForm # Importer le formulaire approprié
    form = SelectGroupForm()

    # Charger les groupes pour le formulaire
    groups = db_manager.get_all_groups()
    form.group_id.choices = [(g['id'], f"{g['name']} ({g['department_name']})") for g in groups]
    form.group_id.choices.insert(0, (0, "--- Sélectionnez votre groupe ---"))

    if form.validate_on_submit():
        group_id = form.group_id.data
        group_info = db_manager.get_group_by_id(group_id)

        if not group_info:
            flash('Groupe invalide sélectionné.', 'error')
            return render_template('index.html', form=form)

        # Stocker les informations nécessaires dans la session
        session['booking_step'] = 1
        session['booking_data'] = {
            'group_id': group_id,
            'group_name': group_info['name'],
            'department_name': group_info['department_name'],
            'contact_name': group_info['contact_name'], # Utiliser infos du groupe
            'contact_email': group_info['contact_email'],
            'contact_phone': group_info.get('contact_phone'),
            'selected_slots': [], # Sera: [{'module_id': x, 'date': '...', 'hour': y, 'minutes': z}, ...]
            'participants': [], # Sera: [{'name': '...', 'email': '...'}, ...] (Participants spécifiques à cette session si besoin)
            'uploaded_files_info': [], # Pour les fichiers temporaires
            'selected_global_doc_ids': []
        }
        logger.info(f"Booking Step 1: Group {group_info['name']} selected. Proceeding to formations.")
        return redirect(url_for('formations'))

    # GET request or validation failed
    session.pop('booking_data', None) # Clear session on new visit
    session.pop('booking_step', None)
    session.pop('temp_files_to_clean', None)
    return render_template('index.html', form=form)

# Étape 2: Sélection Modules et Créneaux
@app.route('/formations', methods=['GET', 'POST'])
@check_db_connection
def formations():
    """Étape 2: Sélection des modules et créneaux"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 1:
        flash('Veuillez commencer par sélectionner votre groupe.', 'warning')
        return redirect(url_for('index'))

    booking_data = session['booking_data']
    group_info = db_manager.get_group_by_id(booking_data['group_id'])
    if not group_info:
        flash("Erreur: Groupe non trouvé.", "error")
        return redirect(url_for('index'))

    # Utiliser WTForms pour la validation des slots sélectionnés
    from forms import SelectModulesForm
    form = SelectModulesForm()

    if form.validate_on_submit():
        import json
        try:
            # Valider la structure JSON du champ caché 'selected_slots'
            selected_slots_raw = json.loads(form.selected_slots.data)
            if not isinstance(selected_slots_raw, list): raise ValueError("Invalid format")

            # Nettoyer et valider chaque slot
            selected_slots = []
            for slot in selected_slots_raw:
                # Vérifier la disponibilité serveur ici !
                available = db_manager.check_slot_availability(
                    module_id=int(slot['module_id']),
                    date=slot['date'],
                    hour=int(slot['hour']),
                    minutes=int(slot['minutes'])
                )
                if not available['available']:
                     module = db_manager.get_module_by_id(int(slot['module_id']))
                     flash(f"Le créneau pour '{module['name']}' le {slot['date']} à {slot['hour']}:{slot['minutes']:02d} n'est plus disponible.", 'error')
                     # Recharger la page avec les erreurs, garder les sélections précédentes si possible
                     # (nécessite de passer les données au template pour repeupler JS)
                     modules_db = db_manager.get_all_modules(active_only=True)
                     calendar_json_data = json.dumps(generate_calendar_data()) # Regen calendar data
                     return render_template('formations.html',
                                            form=form, # Passer le formulaire pour erreurs potentielles
                                            booking_data=booking_data,
                                            group_info=group_info,
                                            modules=modules_db,
                                            calendar_data=calendar_json_data,
                                            initial_selected_slots=form.selected_slots.data # Pour repeupler JS
                                            )

                selected_slots.append({
                    'module_id': int(slot['module_id']),
                    'date': slot['date'],
                    'hour': int(slot['hour']),
                    'minutes': int(slot['minutes'])
                    # On récupèrera le nom du module plus tard via l'ID
                })

            if not selected_slots:
                 flash('Veuillez sélectionner au moins un créneau de formation valide.', 'error')
                 # Recharger la page (comme ci-dessus)
                 modules_db = db_manager.get_all_modules(active_only=True)
                 calendar_json_data = json.dumps(generate_calendar_data())
                 return render_template('formations.html',
                                        form=form, booking_data=booking_data, group_info=group_info,
                                        modules=modules_db, calendar_data=calendar_json_data,
                                        initial_selected_slots=form.selected_slots.data)


            # Mettre à jour la session
            booking_data['selected_slots'] = selected_slots
            session['booking_data'] = booking_data
            session['booking_step'] = 2
            logger.info(f"Booking Step 2: {len(selected_slots)} slots selected for group {group_info['name']}. Proceeding to participants.")
            return redirect(url_for('participants'))

        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Erreur traitement slots: {e}", exc_info=True)
            flash("Erreur lors de la sélection des créneaux. Veuillez réessayer.", "error")
            # Recharger la page (comme ci-dessus)
            modules_db = db_manager.get_all_modules(active_only=True)
            calendar_json_data = json.dumps(generate_calendar_data())
            return render_template('formations.html',
                                    form=form, booking_data=booking_data, group_info=group_info,
                                    modules=modules_db, calendar_data=calendar_json_data,
                                    initial_selected_slots=form.selected_slots.data or '[]')


    # GET request
    modules_db = db_manager.get_all_modules(active_only=True)
    calendar_json_data = json.dumps(generate_calendar_data()) # Fetch calendar data

    # Pré-remplir le champ caché si on revient à cette étape
    initial_slots_json = json.dumps(booking_data.get('selected_slots', []))
    form.selected_slots.data = initial_slots_json

    return render_template(
        'formations.html',
        form=form, # Passer le formulaire vide
        booking_data=booking_data,
        group_info=group_info,
        modules=modules_db,
        calendar_data=calendar_json_data,
        initial_selected_slots=initial_slots_json # Pour initialiser JS
    )


# Étape 3: Gestion des Participants
@app.route('/participants', methods=['GET', 'POST'])
@check_db_connection
def participants():
    """Étape 3: Gestion des participants pour la session."""
    if 'booking_data' not in session or session.get('booking_step', 0) < 2:
        flash("Veuillez d'abord sélectionner les modules de formation.", 'warning')
        return redirect(url_for('index')) # Revenir au début si étape sautée

    booking_data = session['booking_data']
    group_info = db_manager.get_group_by_id(booking_data['group_id'])
    if not group_info:
        flash("Erreur: Groupe non trouvé.", "error")
        return redirect(url_for('index'))

    # Récupérer les participants existants du groupe pour pré-remplir/suggestion
    existing_participants = db_manager.get_participants_by_group(booking_data['group_id'])

    # Utiliser WTForms pour valider les participants ajoutés (via JS et champ caché)
    from forms import ParticipantsBookingForm
    form = ParticipantsBookingForm()
    # Passer min/max au formulaire pour la validation
    form.min_participants.data = MIN_PARTICIPANTS
    form.max_participants.data = MAX_PARTICIPANTS

    if form.validate_on_submit():
        import json
        try:
            # participants_json contient la liste des participants sélectionnés/ajoutés pour CETTE réservation
            participants_list = json.loads(form.participants_json.data)
            if not isinstance(participants_list, list): raise ValueError("Invalid format")

            # La validation WTForms a déjà vérifié le nombre et le format basique
            booking_data['participants'] = participants_list # Stocker les participants de la session
            session['booking_data'] = booking_data
            session['booking_step'] = 3
            logger.info(f"Booking Step 3: Added {len(participants_list)} participants for group {group_info['name']}. Proceeding to documents.")
            return redirect(url_for('documents'))

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Erreur traitement participants: {e}", exc_info=True)
            flash("Erreur lors de la gestion des participants. Veuillez réessayer.", "error")
            # Recharger la page GET avec les erreurs

    # GET request
    # Pré-remplir le formulaire avec les participants déjà en session si retour arrière
    initial_participants_json = json.dumps(booking_data.get('participants', []))
    form.participants_json.data = initial_participants_json

    # Récupérer les détails des modules sélectionnés pour affichage
    selected_slots = booking_data.get('selected_slots', [])
    selected_modules_details = []
    module_ids = {slot['module_id'] for slot in selected_slots}
    modules_in_db = {m['id']: m for m in db_manager.get_all_modules(active_only=False) if m['id'] in module_ids}

    for slot in selected_slots:
        module_info = modules_in_db.get(slot['module_id'])
        if module_info:
             selected_modules_details.append({
                 'module_id': slot['module_id'],
                 'module_name': module_info['name'],
                 'date': slot['date'],
                 'hour': slot['hour'],
                 'minutes': slot['minutes']
             })

    return render_template(
        'participants.html',
        form=form, # Passer le formulaire
        booking_data=booking_data,
        group_info=group_info,
        selected_modules=selected_modules_details, # Modules/Créneaux choisis
        existing_participants=existing_participants, # Participants du groupe pour suggestion/pré-remplissage
        initial_participants_json=initial_participants_json, # Pour initialiser JS
        min_participants=MIN_PARTICIPANTS,
        max_participants=MAX_PARTICIPANTS
    )

# Étape 4: Gestion des Documents
@app.route('/documents', methods=['GET', 'POST'])
@check_db_connection
def documents():
    """Étape 4: Gestion des documents."""
    if 'booking_data' not in session or session.get('booking_step', 0) < 3:
        flash("Veuillez d'abord gérer les participants.", 'warning')
        return redirect(url_for('index'))

    booking_data = session['booking_data']
    group_info = db_manager.get_group_by_id(booking_data['group_id'])
    if not group_info:
        flash("Erreur: Groupe non trouvé.", "error")
        return redirect(url_for('index'))

    from forms import DocumentsBookingForm
    form = DocumentsBookingForm()

    # Charger les documents globaux pour le formulaire
    global_docs = db_manager.get_global_documents()
    form.global_documents.choices = [(d['id'], d['filename']) for d in global_docs]

    if form.validate_on_submit():
        # 1. Gérer les fichiers uploadés
        uploaded_files = form.uploaded_documents.data # Liste des FileStorage
        temp_files_to_clean = session.get('temp_files_to_clean', [])
        newly_uploaded_info = []

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Sauvegarde temporaire immédiate
                try:
                    fd, temp_path = tempfile.mkstemp(suffix=f"_{filename}", dir=app.config['UPLOAD_FOLDER'])
                    os.close(fd)
                    file.save(temp_path)
                    file_size = os.path.getsize(temp_path)

                    if file_size > app.config['MAX_CONTENT_LENGTH']:
                         flash(f"Fichier '{filename}' trop volumineux.", "error")
                         try: os.remove(temp_path)
                         except OSError: pass
                         continue # Skip

                    temp_files_to_clean.append(temp_path)
                    newly_uploaded_info.append({
                        'filename': filename,
                        'filetype': file.content_type or 'application/octet-stream',
                        'filesize': file_size,
                        'temp_path': temp_path # Garder chemin temporaire pour lecture lors de finalize
                    })
                    logger.info(f"Fichier temporaire sauvegardé: {temp_path}")
                except Exception as e:
                    logger.error(f"Erreur sauvegarde fichier temp {filename}: {e}")
                    flash(f"Erreur lors de la sauvegarde temporaire de {filename}.", "error")
                    # Peut-être rediriger ici pour éviter état incohérent?
                    return redirect(url_for('documents'))

            elif file and file.filename:
                flash(f"Type de fichier non autorisé pour '{file.filename}'.", "warning")

        # Mettre à jour la liste des fichiers uploadés dans la session
        # Éviter les doublons si l'utilisateur revient sur cette page
        existing_temp_paths = {f['temp_path'] for f in booking_data.get('uploaded_files_info', [])}
        final_uploaded_info = booking_data.get('uploaded_files_info', [])
        for new_file in newly_uploaded_info:
             if new_file['temp_path'] not in existing_temp_paths:
                  final_uploaded_info.append(new_file)

        booking_data['uploaded_files_info'] = final_uploaded_info
        session['temp_files_to_clean'] = temp_files_to_clean # MAJ liste des fichiers à nettoyer

        # 2. Gérer les documents globaux sélectionnés et infos additionnelles
        booking_data['selected_global_doc_ids'] = form.global_documents.data # Liste d'IDs
        booking_data['additional_info'] = form.additional_info.data

        session['booking_data'] = booking_data
        session['booking_step'] = 4
        logger.info(f"Booking Step 4: Documents processed for group {group_info['name']}. Proceeding to confirmation.")
        return redirect(url_for('confirmation'))

    # GET request
    # Pré-remplir le formulaire si retour arrière
    form.additional_info.data = booking_data.get('additional_info', '')
    form.global_documents.data = booking_data.get('selected_global_doc_ids', [])

    return render_template(
        'documents.html',
        form=form,
        booking_data=booking_data,
        group_info=group_info,
        uploaded_files=booking_data.get('uploaded_files_info', []), # Afficher les fichiers déjà uploadés
        allowed_extensions=', '.join(ALLOWED_EXTENSIONS)
    )


# Étape 5: Confirmation
@app.route('/confirmation', methods=['GET']) # Confirmation est juste une vue
@check_db_connection
def confirmation():
    """Étape 5: Confirmation finale."""
    if 'booking_data' not in session or session.get('booking_step', 0) < 4:
        flash("Veuillez compléter les étapes précédentes.", 'warning')
        return redirect(url_for('index'))

    booking_data = session['booking_data']
    group_info = db_manager.get_group_by_id(booking_data['group_id'])
    if not group_info:
        flash("Erreur: Groupe non trouvé.", "error")
        return redirect(url_for('index'))

    # Préparer les données pour l'affichage
    display_data = booking_data.copy()

    # Récupérer les noms des modules
    module_ids = {slot['module_id'] for slot in booking_data.get('selected_slots', [])}
    modules_in_db = {m['id']: m for m in db_manager.get_all_modules(active_only=False) if m['id'] in module_ids}
    display_data['selected_slots_details'] = []
    for slot in booking_data.get('selected_slots', []):
        module = modules_in_db.get(slot['module_id'])
        if module:
            display_data['selected_slots_details'].append({**slot, 'module_name': module['name']})

    # Récupérer les noms des documents globaux
    global_doc_ids = booking_data.get('selected_global_doc_ids', [])
    if global_docs: # S'assurer que global_docs est défini
         global_docs_in_db = {d['id']: d for d in global_docs if d['id'] in global_doc_ids}
         display_data['selected_global_docs_details'] = [global_docs_in_db[gid] for gid in global_doc_ids if gid in global_docs_in_db]
    else:
         # Essayer de les récupérer si pas déjà fait
         try:
             global_docs_list = db_manager.get_global_documents()
             global_docs_in_db = {d['id']: d for d in global_docs_list if d['id'] in global_doc_ids}
             display_data['selected_global_docs_details'] = [global_docs_in_db[gid] for gid in global_doc_ids if gid in global_docs_in_db]
         except Exception:
             display_data['selected_global_docs_details'] = [] # Fallback


    session['booking_step'] = 5 # Marquer comme étant à l'étape confirmation

    # Formulaire simple pour le bouton finaliser et option email
    from forms import FinalConfirmationForm
    form = FinalConfirmationForm()
    form.send_confirmation.data = True # Cocher par défaut

    return render_template('confirmation.html',
                           form=form,
                           booking_data=display_data,
                           group_info=group_info)

# Étape 6: Finalisation (POST depuis confirmation)
@app.route('/finalize', methods=['POST'])
@check_db_connection
def finalize():
    """Finalise les réservations et enregistre en base."""
    if 'booking_data' not in session or session.get('booking_step', 0) < 5:
        flash('Session invalide ou étape de confirmation non atteinte.', 'error')
        return redirect(url_for('index'))

    from forms import FinalConfirmationForm
    form = FinalConfirmationForm() # Recréer pour valider le POST

    if not form.validate_on_submit():
         flash("Erreur lors de la soumission du formulaire de confirmation.", "error")
         # Rediriger vers la page de confirmation GET pour afficher les erreurs potentielles du formulaire
         # (même si ici il n'y a que la checkbox, c'est une bonne pratique)
         return redirect(url_for('confirmation'))

    booking_data = session['booking_data']
    group_id = booking_data['group_id']
    send_confirmation_email_flag = form.send_confirmation.data
    temp_files_to_clean = session.get('temp_files_to_clean', [])
    processed_temp_files = set()
    created_session_ids = []
    errors_occurred = False
    email_sending_failed = False

    # --- Transaction Base de Données ---
    conn = None
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # 1. Re-vérifier la disponibilité des créneaux DANS la transaction
        logger.info("Vérification finale des créneaux...")
        slots_ok = True
        for slot in booking_data['selected_slots']:
            cursor.execute("""
                SELECT s.id FROM sessions s
                WHERE s.module_id = %s AND s.session_date = %s AND s.start_hour = %s AND s.start_minutes = %s
                  AND s.status != 'canceled' FOR UPDATE
            """, (slot['module_id'], slot['date'], slot['hour'], slot['minutes']))
            if cursor.fetchone():
                slots_ok = False
                module = db_manager.get_module_by_id(slot['module_id']) # Fetch name for message
                flash(f"Le créneau pour '{module['name'] if module else 'ID:'+str(slot['module_id'])}' le {slot['date']} n'est plus disponible.", 'error')
                break # Arrêter la vérification

        if not slots_ok:
            raise ValueError("Conflit de créneau détecté.")
        logger.info("Créneaux disponibles.")

        # 2. Créer les sessions
        logger.info(f"Création de {len(booking_data['selected_slots'])} sessions...")
        for slot in booking_data['selected_slots']:
            session_sql = """
                INSERT INTO sessions (module_id, group_id, session_date, start_hour, start_minutes,
                                      duration_minutes, status, location, additional_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            # Récupérer la durée du module
            module_info = db_manager.get_module_by_id(slot['module_id'])
            duration = module_info.get('duration_minutes', 90) if module_info else 90

            session_params = (
                slot['module_id'], group_id, slot['date'], slot['hour'], slot['minutes'],
                duration, 'confirmed', 'Sur site', booking_data.get('additional_info')
            )
            cursor.execute(session_sql, session_params)
            session_id = cursor.fetchone()[0]
            created_session_ids.append(session_id)
            logger.info(f"Session {session_id} créée.")

            # 3. Associer les participants à la session via la table attendances
            participants = booking_data.get('participants', [])
            # Si 'participants' contient la liste spécifique à la session:
            # if participants:
            #     # Insérer/Récupérer ces participants et lier à attendances
            #     # ... Logique complexe ...
            # else: # Sinon, lier tous les participants du groupe
            link_ok = db_manager.link_participants_to_session(session_id, group_id, cursor)
            if not link_ok:
                 raise ValueError(f"Erreur liaison participants session {session_id}.")

            # 4. Gérer les documents pour CETTE session
            # 4a. Documents uploadés (enregistrer et associer)
            for doc_info in booking_data.get('uploaded_files_info', []):
                temp_path = doc_info.get('temp_path')
                if temp_path and os.path.exists(temp_path) and temp_path not in processed_temp_files:
                     try:
                         with open(temp_path, 'rb') as f:
                             file_data = f.read()
                         doc_db_data = {
                             'filename': doc_info['filename'], 'filetype': doc_info['filetype'],
                             'filesize': doc_info['filesize'], 'filedata': psycopg2.Binary(file_data),
                             'description': 'Document ajouté lors de la réservation', 'is_global': False,
                             'uploaded_by_id': None # Ou l'ID de l'admin si applicable
                         }
                         doc_db_id = db_manager.save_document(doc_db_data, cursor)
                         if not doc_db_id: raise ValueError(f"Erreur sauvegarde document {doc_info['filename']}")

                         assoc_ok = db_manager.associate_document_to_session(doc_db_id, session_id, cursor)
                         if not assoc_ok: raise ValueError(f"Erreur association document {doc_db_id} session {session_id}")

                         processed_temp_files.add(temp_path) # Marquer comme traité
                         logger.info(f"Document {doc_info['filename']} (ID:{doc_db_id}) traité pour session {session_id}.")

                     except Exception as doc_err:
                          logger.error(f"Erreur traitement document {doc_info.get('filename')} pour session {session_id}: {doc_err}")
                          raise ValueError(f"Erreur traitement document {doc_info.get('filename')}.") from doc_err
                elif temp_path in processed_temp_files:
                     # Déjà traité pour une autre session de la même réservation, on l'associe juste
                     # Il faut récupérer l'ID du document déjà créé. Complexe sans ORM.
                     # Pour simplifier : on suppose que save_document gère les doublons ou on ne le traite qu'une fois.
                     # Ici, on le traite une fois grâce à processed_temp_files.
                     pass
                elif temp_path:
                     logger.warning(f"Fichier temporaire introuvable: {temp_path}")


            # 4b. Documents globaux (associer)
            for global_doc_id in booking_data.get('selected_global_doc_ids', []):
                 assoc_ok = db_manager.associate_document_to_session(global_doc_id, session_id, cursor)
                 if not assoc_ok:
                     logger.warning(f"Echec association doc global {global_doc_id} session {session_id} (peut-être déjà associé).")
                     # Ne pas faire échouer la transaction pour ça a priori

        # Si tout s'est bien passé, commiter la transaction
        conn.commit()
        logger.info(f"Réservation finalisée avec succès pour groupe {group_id}. Sessions créées: {created_session_ids}")
        add_activity_log_wrapper('booking_finalized',
                                user_info={'group_id': group_id, 'email': booking_data['contact_email']},
                                details={'session_ids': created_session_ids})

    except Exception as e:
        errors_occurred = True
        logger.error(f"Erreur lors de la finalisation pour groupe {group_id}: {e}", exc_info=True)
        flash(f"Une erreur majeure est survenue lors de la finalisation : {str(e)}", 'error')
        if conn:
            conn.rollback() # Annuler la transaction
        # Garder la session pour réessayer ?
        session['booking_step'] = 5 # Remettre à l'étape confirmation
        return redirect(url_for('confirmation'))
    finally:
        # Fermer curseur et connexion
        if cursor: cursor.close()
        if conn: db_manager.release_connection(conn)
        # Nettoyer les fichiers temporaires traités, même si erreur après commit (peu probable)
        logger.info(f"Nettoyage des fichiers temporaires traités: {processed_temp_files}")
        for temp_path in processed_temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Nettoyé: {temp_path}")
            except OSError as clean_err:
                logger.error(f"Erreur nettoyage fichier temp {temp_path}: {clean_err}")

    # --- Post-Transaction ---
    if not errors_occurred:
        # Envoyer les emails de confirmation si demandé
        if send_confirmation_email_flag and created_session_ids:
            logger.info(f"Envoi des emails de confirmation pour {len(created_session_ids)} sessions...")
            from utils import send_session_confirmation_email # Importer la fonction d'envoi
            for s_id in created_session_ids:
                try:
                    # La fonction d'envoi gère la récupération des détails
                    send_session_confirmation_email(s_id)
                except Exception as mail_err:
                    logger.error(f"Echec envoi email pour session {s_id}: {mail_err}")
                    email_sending_failed = True

        # Nettoyer la session et rediriger
        session.pop('booking_data', None)
        session.pop('booking_step', None)
        session.pop('temp_files_to_clean', None)

        flash('Vos réservations ont été créées avec succès !', 'success')
        if email_sending_failed:
            flash("Certains emails de confirmation n'ont pas pu être envoyés.", 'warning')

        session['last_booking_group_id'] = group_id # Pour la page de remerciement

        return redirect(url_for('thank_you'))
    else:
         # Normalement géré dans le bloc except, mais double sécurité
         return redirect(url_for('confirmation'))


# Page de Remerciement
@app.route('/thank-you')
def thank_you():
    """Page de remerciement après finalisation"""
    group_id = session.pop('last_booking_group_id', None)
    email = "l'adresse indiquée"
    group_name = "votre groupe"
    if group_id and db_manager:
         group_info = db_manager.get_group_by_id(group_id)
         if group_info:
             email = group_info['contact_email']
             group_name = group_info['name']

    return render_template('thank_you.html', email=email, group_name=group_name)


# --- API Routes (adaptées) ---
# (Adaptation partielle - vérifier la logique et sécurité)

@app.route('/api/ping', methods=['GET'])
def ping():
    """API pour vérifier la connexion serveur et DB"""
    db_ok = db_manager.ping() if db_manager else False
    if db_ok:
        return jsonify({"status": "ok", "message": "Serveur et DB opérationnels."}), 200
    else:
        return jsonify({"status": "error", "message": "Erreur connexion DB."}), 503

@app.route('/api/calendar_data', methods=['GET'])
@check_db_connection
def get_calendar_data():
    """API pour récupérer les données du calendrier (sessions)."""
    # Ajouter filtres si nécessaire (mois, module_id, department_id)
    # month = request.args.get('month')
    # module_id = request.args.get('module_id')
    try:
        # Utiliser la fonction helper generate_calendar_data adaptée
        calendar_data = generate_calendar_data()
        return jsonify(calendar_data)
    except Exception as e:
        logger.error(f"API Erreur génération calendrier: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la génération du calendrier."}), 500


# --- Admin Routes (adaptées) ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Page de connexion admin"""
    if current_user.is_authenticated: # Utilise Flask-Login
        return redirect(url_for('admin_dashboard'))

    # Utiliser WTForms pour le login
    from forms import LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data

        user_data = db_manager.get_admin_user_by_username(username) if db_manager else None

        if user_data and check_password_hash(user_data['password_hash'], password):
            admin_obj = AdminUser(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
            login_user(admin_obj, remember=remember) # Flask-Login gère la session
            flash('Connexion réussie !', 'success')
            add_activity_log_wrapper('admin_login_success')
            next_page = request.args.get('next')
            # Ajouter validation next_page ici
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
            add_activity_log_wrapper('admin_login_failed', details={'username': username})
            # time.sleep(1) # Ralentir brute-force

    return render_template('admin_login.html', form=form) # Passer le formulaire au template

@app.route('/admin/logout')
@login_required # Utilise Flask-Login
def admin_logout():
    """Déconnexion admin"""
    add_activity_log_wrapper('admin_logout')
    logout_user() # Géré par Flask-Login
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
@check_db_connection
def admin_dashboard():
    """Tableau de bord admin"""
    try:
        stats = db_manager.get_dashboard_stats()
        recent_logs = db_manager.get_activity_logs(limit=10) # Exemple: 10 logs récents
        stats['recent_activity'] = recent_logs

        # Récupérer des données supplémentaires si nécessaire pour le tableau de bord
        upcoming_sessions = [] # db_manager.get_upcoming_sessions(...)
        pending_feedback = [] # db_manager.get_feedback_by_status('new')

        return render_template('admin_dashboard.html', stats=stats,
                               upcoming_sessions=upcoming_sessions,
                               pending_feedback=pending_feedback)
    except Exception as e:
        logger.error(f"Erreur chargement admin dashboard: {e}", exc_info=True)
        flash('Erreur chargement tableau de bord.', 'error')
        # Peut-être rediriger vers une page d'erreur simple ou login
        return redirect(url_for('admin_login'))

# --- CRUD Admin (Exemples pour Départements et Modules) ---

# Departments List
@app.route('/admin/departments')
@login_required
@check_db_connection
def admin_departments():
    departments = db_manager.get_all_departments()
    return render_template('admin/departments_list.html', departments=departments)

# Create Department
@app.route('/admin/departments/new', methods=['GET', 'POST'])
@login_required
@check_db_connection
def admin_new_department():
    from forms import DepartmentForm
    form = DepartmentForm()
    if form.validate_on_submit():
        data = {'code': form.code.data, 'name': form.name.data, 'description': form.description.data}
        dept_id = db_manager.create_department(data)
        if dept_id == -1:
            flash('Le code département existe déjà.', 'error')
        elif dept_id:
            add_activity_log_wrapper('department_created', entity_type='Department', entity_id=dept_id, details=data)
            flash('Département créé avec succès.', 'success')
            return redirect(url_for('admin_departments'))
        else:
            flash('Erreur lors de la création du département.', 'error')
    return render_template('admin/department_form.html', form=form, title="Nouveau Département")

# Edit Department
@app.route('/admin/departments/edit/<int:dept_id>', methods=['GET', 'POST'])
@login_required
@check_db_connection
def admin_edit_department(dept_id):
    department = db_manager.get_department_by_id(dept_id)
    if not department:
        flash('Département non trouvé.', 'error')
        return redirect(url_for('admin_departments'))

    from forms import DepartmentForm
    form = DepartmentForm(data=department) # Pré-remplir

    if form.validate_on_submit():
        data = {'code': form.code.data, 'name': form.name.data, 'description': form.description.data}
        success = db_manager.update_department(dept_id, data)
        if success:
            add_activity_log_wrapper('department_updated', entity_type='Department', entity_id=dept_id, details=data)
            flash('Département mis à jour.', 'success')
            return redirect(url_for('admin_departments'))
        else:
            flash('Erreur lors de la mise à jour (code peut-être dupliqué).', 'error')
    return render_template('admin/department_form.html', form=form, title="Modifier Département", department=department)

# Delete Department (Ajouter confirmation JS !)
@app.route('/admin/departments/delete/<int:dept_id>', methods=['POST']) # Utiliser POST pour suppression
@login_required
@check_db_connection
def admin_delete_department(dept_id):
    # Ajouter vérification CSRF si pas déjà fait via form
    department = db_manager.get_department_by_id(dept_id) # Pour log
    success = db_manager.delete_department(dept_id)
    if success:
         add_activity_log_wrapper('department_deleted', entity_type='Department', entity_id=dept_id, details={'name': department['name'] if department else 'N/A'})
         flash('Département supprimé.', 'success')
    else:
         flash('Erreur lors de la suppression (vérifier groupes associés).', 'error')
    return redirect(url_for('admin_departments'))


# --- CRUD pour Modules (similaire à Départements) ---
@app.route('/admin/modules')
# ... List modules ...

@app.route('/admin/modules/new', methods=['GET', 'POST'])
# ... Create module ...

@app.route('/admin/modules/edit/<int:module_id>', methods=['GET', 'POST'])
# ... Edit module ...

@app.route('/admin/modules/delete/<int:module_id>', methods=['POST'])
# ... Delete module ...


# --- Ajouter les routes pour les autres entités: Groups, Sessions, Participants, Documents ... ---


# --- User Routes (Tableau de bord via lien tokenisé) ---

# Page pour demander le lien
@app.route('/user/access', methods=['GET', 'POST'])
def request_user_dashboard_link():
     from forms import UserDashboardLinkForm
     form = UserDashboardLinkForm()
     if form.validate_on_submit():
         email = form.email.data.lower().strip()
         # Vérifier si un groupe existe avec cet email de contact
         groups = db_manager.get_groups_by_contact_email(email) # Nouvelle méthode à créer dans db_manager

         if groups:
             # Générer un token (exemple simple, expire après 1h)
             token = ts.dumps(email, salt='user-dashboard-access')
             dashboard_url = url_for('user_dashboard', token=token, _external=True)

             # Envoyer l'email (créer le template email/user_dashboard_link.html)
             subject = EMAIL_CONFIG['templates']['user_dashboard_link']['subject']
             html_body = render_template('email/user_dashboard_link.html', dashboard_url=dashboard_url)
             text_body = f"Cliquez ici pour accéder à votre tableau de bord : {dashboard_url}"

             from utils import send_email # Importer la fonction générique
             send_email(subject, [email], text_body, html_body)

             flash("Un lien d'accès a été envoyé à votre adresse email (s'il correspond à un contact de groupe).", 'info')
             return redirect(url_for('index'))
         else:
             flash("Aucun groupe trouvé avec cet email de contact.", 'warning')

     return render_template('user/request_link.html', form=form)


@app.route('/user/dashboard')
@check_db_connection
def user_dashboard():
    """Tableau de bord utilisateur via Token"""
    token = request.args.get('token')
    if not token:
        flash("Lien d'accès manquant ou invalide.", "error")
        return redirect(url_for('request_user_dashboard_link'))

    try:
        # Valider le token (expire après 1 heure = 3600s)
        email = ts.loads(token, salt='user-dashboard-access', max_age=3600)
    except SignatureExpired:
        flash("Votre lien d'accès a expiré. Veuillez en demander un nouveau.", "warning")
        return redirect(url_for('request_user_dashboard_link'))
    except BadTimeSignature:
        flash("Lien d'accès invalide ou corrompu.", "error")
        return redirect(url_for('request_user_dashboard_link'))
    except Exception as e:
         logger.error(f"Erreur validation token: {e}")
         flash("Erreur lors de la validation du lien.", "error")
         return redirect(url_for('request_user_dashboard_link'))


    # Récupérer les données pour cet email de contact
    user_groups = db_manager.get_groups_by_contact_email(email)
    if not user_groups:
         flash("Impossible de trouver les informations pour cet utilisateur.", "error")
         return redirect(url_for('request_user_dashboard_link'))

    # Pour simplifier, on prend le premier groupe (ou on pourrait lister tous les groupes)
    group_id = user_groups[0]['id']
    group_info = user_groups[0]

    # Récupérer les sessions, participants, documents pour ce groupe
    user_sessions = db_manager.get_sessions_for_group(group_id) # Nouvelle méthode db_manager
    group_participants = db_manager.get_participants_by_group(group_id)
    global_documents = db_manager.get_global_documents()
    # Récupérer les documents spécifiques aux sessions du groupe ? Plus complexe.

    today_date_str = datetime.date.today().isoformat()

    return render_template(
        'user_dashboard.html',
        email=email,
        group_info=group_info,
        user_sessions=user_sessions,
        group_participants=group_participants,
        global_documents=global_documents,
        today_date=today_date_str
    )

# --- Export Routes (Adapter pour utiliser le nouveau schéma) ---
# @app.route('/export/ical')
# ... (Logique à adapter pour récupérer sessions par group_id/email via token)

# --- Helper Functions (certaines déplacées dans utils.py) ---

# Garder generate_calendar_data ici ou le mettre dans utils.py
def generate_calendar_data():
    """Génère les données calendrier depuis les sessions DB."""
    if not db_manager: return []
    try:
        sessions = db_manager.get_all_sessions() # Récupère sessions avec infos module/groupe
        calendar_data = []
        colors = CALENDAR_CONFIG.get('colors', {})
        default_color = colors.get('default', '#3788d8')

        for session in sessions:
             if session['status'] == 'canceled': continue # Ne pas afficher les annulées
             try:
                 start_dt = datetime.datetime.combine(
                     datetime.date.fromisoformat(session['session_date']),
                     datetime.time(session['start_hour'], session['minutes'])
                 )
                 # Calculer end_dt à partir de la durée du module si disponible
                 module = db_manager.get_module_by_id(session['module_id'])
                 duration = module.get('duration_minutes', 90) if module else 90
                 end_dt = start_dt + datetime.timedelta(minutes=duration)

                 dept_code = session.get('department_code', 'default')
                 color = colors.get(dept_code, default_color)

                 calendar_data.append({
                     'id': str(session['id']),
                     'title': f"{session['module_name']} ({session['group_name']})",
                     'start': start_dt.isoformat(),
                     'end': end_dt.isoformat(),
                     'backgroundColor': color,
                     'borderColor': color,
                     'extendedProps': {
                         'session_id': session['id'],
                         'module_name': session['module_name'],
                         'group_name': session['group_name'],
                         'group_contact': session.get('group_contact'),
                         'department_name': session.get('department_name', 'N/A'),
                         # Ajouter d'autres infos utiles pour le popup du calendrier
                     }
                 })
             except Exception as item_err:
                 logger.warning(f"Skipping session ID {session.get('id')} in calendar gen: {item_err}")
                 continue

        return calendar_data
    except Exception as e:
        logger.error(f"Erreur génération données calendrier: {e}", exc_info=True)
        return []

# --- Main Execution ---
if __name__ == '__main__':
    if db_manager is None:
        print("CRITICAL: Database initialization failed. Application cannot run.", file=sys.stderr)
        sys.exit(1)

    # S'assurer que le dossier UPLOAD_FOLDER existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.run(debug=DEBUG, host='0.0.0.0', port=5000) # threaded=True est souvent par défaut
