import os
import json
import logging
import calendar
import datetime
import tempfile
import sys # Importé pour sys.stderr et sys.exit
from typing import Dict, List, Any, Tuple, Optional
from functools import wraps
from urllib.parse import urljoin
from markupsafe import escape # Pour échapper le HTML dans les emails/logs

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    session, flash, send_file, abort, g
)
from flask_mail import Mail, Message
# Import Flask-WTF for CSRF protection (install it: pip install Flask-WTF)
from flask_wtf.csrf import CSRFProtect, CSRFError

from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash # Use check_password_hash
import psycopg2 # Import psycopg2 pour psycopg2.Binary
import psycopg2.extras

from config import (
    DATABASE_URL, FORMATION_MODULES, DEPARTMENTS, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
    AVAILABLE_MONTHS, EMAIL_CONFIG, ADMIN_PASSWORD_HASH, APP_NAME, CDN_CONFIG,
    SYSTEM_CONFIG, ALLOWED_EXTENSIONS, CALENDAR_CONFIG,
    DEBUG,
    APP_VERSION  # <--- AJOUTER DEBUG ICI
)
# Import db_manager instance, handle potential initialization failure
try:
    from db_manager import db_manager
    if db_manager is None:
        raise ImportError("db_manager failed to initialize.")
except (ImportError, ConnectionError) as e:
    # Log critical error and potentially exit or run in a degraded mode
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"Failed to import or initialize db_manager: {e}. Application cannot start properly.")
    # Depending on deployment, you might exit here:
    # import sys
    # sys.exit("Database connection failed.")
    # For now, let Flask start but routes using db_manager will fail.
    db_manager = None # Ensure it's None if import failed

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, SYSTEM_CONFIG.get('log_level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(seconds=SYSTEM_CONFIG.get('session_timeout', 3600))

# Configuration du dossier pour les uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), SYSTEM_CONFIG.get('temp_folder', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = SYSTEM_CONFIG.get('max_upload_size', 10 * 1024 * 1024)

# Configuration de l'envoi d'emails
app.config['MAIL_SERVER'] = EMAIL_CONFIG['smtp_server']
app.config['MAIL_PORT'] = EMAIL_CONFIG['smtp_port']
app.config['MAIL_USERNAME'] = EMAIL_CONFIG['username']
app.config['MAIL_PASSWORD'] = EMAIL_CONFIG['password']
app.config['MAIL_USE_TLS'] = EMAIL_CONFIG['use_tls']
app.config['MAIL_USE_SSL'] = False # Typically use TLS on port 587
mail = Mail(app)

# Initialiser la protection CSRF
csrf = CSRFProtect(app)

# --- Decorators ---
def login_required(f):
    """Décorateur pour exiger l'authentification admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('admin_login', next=request.url))
        g.is_admin = True # Set a global flag for the request context
        return f(*args, **kwargs)
    return decorated_function

def check_db_connection(f):
    """Decorator to check if db_manager is available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if db_manager is None:
            logger.critical("Database manager is not available.")
            flash("Erreur critique: Impossible de se connecter à la base de données. Veuillez contacter l'administrateur.", "error")
            # Redirect to a static error page or index
            return redirect(url_for('index')) # Or render_template('errors/db_error.html')
        return f(*args, **kwargs)
    return decorated_function


# --- Utility Functions ---
def allowed_file(filename):
    """Vérifie si le type de fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_request_ip():
    """Get user IP address from request."""
    # Trust X-Forwarded-For if behind a proxy
    if request.headers.getlist("X-Forwarded-For"):
       ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip() # Get first IP if multiple
    # Otherwise, use remote_addr
    elif request.remote_addr:
       ip = request.remote_addr
    # Fallback if neither is available
    else:
        ip = "Unknown"
    return ip

# --- Context Processors and Template Filters ---
@app.context_processor
def inject_template_globals():
    """Injecter des variables globales dans tous les templates"""
    return {
        'app_name': APP_NAME,
        'app_version': APP_VERSION,
        'current_year': datetime.datetime.now().year,
        'cdn': CDN_CONFIG,
        'departments': DEPARTMENTS,
        'formation_modules': FORMATION_MODULES,
        'is_admin': session.get('admin_logged_in', False) # Inject admin status
    }

@app.template_filter('format_date')
def format_date_filter(date_input):
    """Filtre pour formater les dates (string ou date object)"""
    if not date_input: return ""
    try:
        if isinstance(date_input, (datetime.date, datetime.datetime)):
            date_obj = date_input
        else:
            date_obj = datetime.datetime.strptime(str(date_input), '%Y-%m-%d').date()

        # Format in French locale if possible, otherwise default
        try:
            import locale
            # Attempt to set French locale (may fail depending on OS support)
            current_locale = locale.getlocale(locale.LC_TIME) # Save current locale
            try:
                locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_TIME, 'French_France.1252') # Windows
                except locale.Error:
                     logger.debug("French locale not available for date formatting.") # Use debug level
            formatted = date_obj.strftime('%d %B %Y')
            locale.setlocale(locale.LC_TIME, current_locale) # Restore original locale
            return formatted
        except ImportError:
             return date_obj.strftime('%d %B %Y') # Fallback if locale module fails
        except Exception as loc_err:
             logger.warning(f"Locale setting failed during date formatting: {loc_err}")
             return date_obj.strftime('%d %B %Y') # Fallback
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not format date '{date_input}': {e}")
        return str(date_input) # Return original string on error

@app.template_filter('format_datetime')
def format_datetime_filter(datetime_input):
    """Filtre pour formater les dates avec heure (string ou datetime object)"""
    if not datetime_input: return ""
    try:
        if isinstance(datetime_input, datetime.datetime):
             date_obj = datetime_input
        else:
            # Try ISO format first, then adapt if needed
            try:
                # Handle potential timezone info if present
                dt_str = str(datetime_input).replace('Z', '+00:00')
                if '.' in dt_str: # Handle microseconds if present
                    dt_str = dt_str.split('.')[0]
                date_obj = datetime.datetime.fromisoformat(dt_str)
            except ValueError:
                # Add other potential formats if necessary
                date_obj = datetime.datetime.strptime(str(datetime_input), '%Y-%m-%d %H:%M:%S') # Example fallback

        # Format in French locale if possible
        try:
            import locale
            current_locale = locale.getlocale(locale.LC_TIME)
            try:
                locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
            except locale.Error:
                 try:
                    locale.setlocale(locale.LC_TIME, 'French_France.1252')
                 except locale.Error:
                    logger.debug("French locale not available for datetime formatting.")
            formatted = date_obj.strftime('%d %B %Y à %H:%M')
            locale.setlocale(locale.LC_TIME, current_locale) # Restore
            return formatted
        except ImportError:
            return date_obj.strftime('%d %B %Y at %H:%M') # Fallback
        except Exception as loc_err:
             logger.warning(f"Locale setting failed during datetime formatting: {loc_err}")
             return date_obj.strftime('%d %B %Y at %H:%M') # Fallback
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not format datetime '{datetime_input}': {e}")
        return str(datetime_input)

@app.template_filter('filesizeformat')
def filesizeformat_filter(size_bytes):
    """Filtre pour formater la taille des fichiers"""
    if size_bytes is None: return "0 o"
    try:
        size = int(size_bytes)
        if size < 0: return "0 o" # Handle potential negative values
        if size < 1024:
            return f"{size} o"
        elif size < 1024**2:
            return f"{size/1024:.1f} Ko"
        elif size < 1024**3:
            return f"{size/(1024**2):.1f} Mo"
        else:
            return f"{size/(1024**3):.1f} Go"
    except (ValueError, TypeError):
        logger.warning(f"Could not format file size '{size_bytes}'")
        return "N/A"

@app.template_filter('nl2br')
def nl2br_filter(text):
    """Filtre pour convertir les sauts de ligne en balises <br>"""
    if not text: return ""
    # Ensure text is string and escape HTML before replacing newlines
    return escape(str(text)).replace('\n', '<br>\n')


# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 Not Found: {request.url} (Referrer: {request.referrer})")
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 Internal Server Error: {e} at {request.url}", exc_info=True)
    # Optionally log more details or notify admins
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(e):
    logger.warning(f"403 Forbidden: Access denied to {request.url}")
    return render_template('errors/403.html'), 403

@app.errorhandler(413) # Request Entity Too Large (File Upload)
def request_entity_too_large(e):
    logger.warning(f"413 Request Entity Too Large: File upload exceeded limit at {request.url}")
    flash(f"Le fichier téléchargé dépasse la taille maximale autorisée ({app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f} Mo).", "error")
    # Redirect back to the previous page if possible
    return redirect(request.referrer or url_for('index'))


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    logger.warning(f"CSRF validation failed: {e.description} from IP {get_request_ip()}")
    flash('La session a expiré ou la requête est invalide. Veuillez réessayer.', 'error')
    return redirect(request.referrer or url_for('index'))


# --- Main Routes (Booking Flow) ---

@app.route('/', methods=['GET', 'POST'])
@check_db_connection
def index():
    """Page d'accueil - Étape 1: Sélection du département"""
    if request.method == 'POST':
        # Validate input
        department = request.form.get('service') # Match form field name
        contact = request.form.get('contact', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        errors = False
        if not department:
            flash('Veuillez sélectionner un service.', 'error')
            errors = True
        if not contact:
            flash('Veuillez entrer le nom du responsable.', 'error')
            errors = True
        if not email: # Basic email format check might be added here
            flash('Veuillez entrer une adresse email valide.', 'error')
            errors = True
        # Add more validation if needed (e.g., phone format)

        if errors:
            return render_template('index.html', departments=DEPARTMENTS,
                                   form_data=request.form) # Repopulate form

        # Store initial data in session
        session['booking_step'] = 1
        session['booking_data'] = {
            'service': department, # Use 'service' key consistently
            'department_name': next((d['name'] for d in DEPARTMENTS if d['id'] == department), department),
            'contact': contact,
            'email': email,
            'phone': phone,
            'modules': [],
            'participants': [],
            'documents': [], # Will store processed document info
            'selected_global_documents': []
        }
        logger.info(f"Booking Step 1 completed for {email}, service {department}. Proceeding to formations.")
        return redirect(url_for('formations'))

    # GET request
    session.pop('booking_data', None) # Clear session on new visit to index
    session.pop('booking_step', None)
    session.pop('temp_files_to_clean', None) # Clear any leftover temp files list
    return render_template('index.html', departments=DEPARTMENTS)


@app.route('/formations', methods=['GET'])
@check_db_connection
def formations():
    """Étape 2: Sélection des modules de formation et créneaux"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 1:
        flash('Veuillez commencer par sélectionner votre service.', 'warning')
        return redirect(url_for('index'))

    booking_data = session['booking_data']
    session['booking_step'] = 2

    # Générer les données du calendrier
    try:
        # Pass department to filter already booked slots for this department if needed?
        # For now, just show all bookings.
        calendar_data = generate_calendar_data(current_month=AVAILABLE_MONTHS[0]['id'])
    except Exception as e:
        logger.error(f"Erreur lors de la génération des données du calendrier: {e}")
        flash("Erreur lors du chargement des disponibilités du calendrier.", "error")
        calendar_data = []

    return render_template(
        'formations.html',
        # Pass individual variables for clarity in template
        service=booking_data['service'], # Use 'service' consistently
        service_name=booking_data['department_name'],
        contact=booking_data['contact'],
        email=booking_data['email'],
        phone=booking_data.get('phone'),
        # Pass modules and months config
        formations=FORMATION_MODULES, # Use 'formations' to match template
        months=AVAILABLE_MONTHS,
        calendar_data=json.dumps(calendar_data), # Pass as JSON for JS
        # Pass existing selections if returning to this step
        selected_modules_data=booking_data.get('modules', [])
    )


@app.route('/participants', methods=['POST']) # Only POST makes sense to proceed
@check_db_connection
def participants():
    """Étape 3: Gestion des participants"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 2:
        flash('Veuillez d\'abord sélectionner les modules de formation.', 'warning')
        # Redirect back to formations, preserving initial data if possible
        if 'booking_data' in session:
             # Need to pass back the initial data to formations route
             bd = session['booking_data']
             return redirect(url_for('formations',
                                     department=bd.get('service'),
                                     contact=bd.get('contact'),
                                     email=bd.get('email'),
                                     phone=bd.get('phone')))
        else:
             return redirect(url_for('index'))

    booking_data = session['booking_data']

    # Process selected modules from the form
    selected_modules = []
    has_selection = False
    for module in FORMATION_MODULES:
        module_id = module['id']
        # Check if data for this module was submitted (e.g., hidden fields)
        date = request.form.get(f"date_{module_id}") # Match name in formations.html form
        hour_str = request.form.get(f"hour_{module_id}")
        minutes_str = request.form.get(f"minutes_{module_id}")

        if date and hour_str and minutes_str:
            try:
                hour = int(hour_str)
                minutes = int(minutes_str)
                # Basic validation for date/time format could be added here
                selected_modules.append({
                    'formation_id': module_id, # Use 'formation_id' consistently
                    'formation_name': module['name'],
                    'date': date,
                    'hour': hour,
                    'minutes': minutes
                })
                has_selection = True
            except (ValueError, TypeError):
                 flash(f"Données de créneau invalides pour le module {module['name']}.", "error")
                 # Redirect back to formations step
                 bd = session['booking_data']
                 return redirect(url_for('formations',
                                         department=bd.get('service'),
                                         contact=bd.get('contact'),
                                         email=bd.get('email'),
                                         phone=bd.get('phone')))

    if not has_selection:
        flash('Veuillez sélectionner au moins un créneau de formation.', 'error')
        bd = session['booking_data']
        return redirect(url_for('formations',
                                department=bd.get('service'),
                                contact=bd.get('contact'),
                                email=bd.get('email'),
                                phone=bd.get('phone')))

    # Update session
    booking_data['modules'] = selected_modules
    session['booking_data'] = booking_data
    session['booking_step'] = 3
    logger.info(f"Booking Step 2 completed for {booking_data['email']}. Selected {len(selected_modules)} modules. Proceeding to participants.")

    return render_template(
        'participants.html',
        # Pass data needed by the template
        service=booking_data['service'],
        service_name=booking_data['department_name'],
        contact=booking_data['contact'],
        email=booking_data['email'],
        phone=booking_data.get('phone'),
        formations=selected_modules, # Pass the selected modules
        participants=booking_data.get('participants', []), # Pass existing participants if any
        min_participants=MIN_PARTICIPANTS,
        max_participants=MAX_PARTICIPANTS
    )


@app.route('/documents', methods=['POST']) # Only POST makes sense
@check_db_connection
def documents():
    """Étape 4: Gestion des documents"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 3:
        flash('Veuillez d\'abord ajouter les participants.', 'warning')
        # Redirect back appropriately
        if session.get('booking_step', 0) == 2:
            return redirect(url_for('participants')) # Should redirect with POST data? No, redirect to GET of prev step
        elif session.get('booking_step', 0) == 1:
             bd = session['booking_data']
             return redirect(url_for('formations',
                                     department=bd.get('service'),
                                     contact=bd.get('contact'),
                                     email=bd.get('email'),
                                     phone=bd.get('phone')))
        else:
            return redirect(url_for('index'))

    booking_data = session['booking_data']

    # Process participants from the form
    participants = []
    participant_count = int(request.form.get('participant_count', 0))

    for i in range(participant_count):
        name = request.form.get(f'participant_name_{i}', '').strip()
        email = request.form.get(f'participant_email_{i}', '').strip().lower()
        department = request.form.get(f'participant_department_{i}', '').strip()

        if name:  # Name is mandatory
            # Add more validation if needed (e.g., email format)
            participants.append({
                'name': name,
                'email': email,
                'department': department
            })

    # Validate participant count
    if not (MIN_PARTICIPANTS <= len(participants) <= MAX_PARTICIPANTS):
        flash(f'Le nombre de participants ({len(participants)}) doit être compris entre {MIN_PARTICIPANTS} et {MAX_PARTICIPANTS}.', 'error')
        # Store submitted participants back in session to repopulate form
        booking_data['participants'] = participants
        session['booking_data'] = booking_data
        # Redirect back to participants step (will be GET, need to handle state)
        # It's complex to redirect back to POST. Better to handle GET for participants.
        # For now, just flashing error might be enough if JS handles list.
        # Consider making participants GETtable or using JS to store state.
        # Simplest for now: just flash and let user re-add if needed.
        return redirect(url_for('participants')) # This will likely lose state if not handled

    # Update session
    booking_data['participants'] = participants
    session['booking_data'] = booking_data
    session['booking_step'] = 4
    logger.info(f"Booking Step 3 completed for {booking_data['email']}. Added {len(participants)} participants. Proceeding to documents.")


    # Get global documents for selection
    try:
        global_documents = db_manager.get_global_documents()
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des documents globaux: {e}")
        global_documents = []
        flash("Erreur lors du chargement des documents de la bibliothèque.", "error")

    return render_template(
        'documents.html',
        booking_data=booking_data, # Pass the whole dict
        global_documents=global_documents,
        allowed_extensions=', '.join(ALLOWED_EXTENSIONS)
    )


@app.route('/confirmation', methods=['POST']) # Only POST makes sense
@check_db_connection
def confirmation():
    """Étape 5: Confirmation finale"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 4:
        flash('Veuillez d\'abord gérer les documents.', 'warning')
        # Redirect back appropriately
        if session.get('booking_step', 0) == 3:
            return redirect(url_for('documents')) # This needs to be GETtable or handle state
        # ... add other steps if needed
        else:
            return redirect(url_for('index'))

    booking_data = session['booking_data']

    # Process form data from documents step
    additional_info = request.form.get('additional_info', '').strip()
    selected_global_documents = request.form.getlist('global_documents') # Assuming checkboxes named 'global_documents'

    # --- Improved File Handling ---
    uploaded_files_info = booking_data.get('uploaded_files_info', []) # Keep existing if returning
    temp_files_to_clean = session.get('temp_files_to_clean', [])
    newly_uploaded_paths = []

    try:
        files = request.files.getlist('documents') # Assuming input name="documents"
        logger.debug(f"Received {len(files)} files for upload.")
        for file in files:
            if file and file.filename: # Check if file object exists and has a name
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Save to a secure temporary location immediately
                    fd, temp_path = tempfile.mkstemp(suffix=f"_{filename}", dir=app.config['UPLOAD_FOLDER'])
                    os.close(fd) # Close file descriptor, save will reopen/write
                    file.save(temp_path)
                    newly_uploaded_paths.append(temp_path) # Track for cleanup THIS request
                    temp_files_to_clean.append(temp_path) # Add to session list for overall cleanup

                    file_size = os.path.getsize(temp_path)
                    logger.info(f"Saved temporary file: {filename} at {temp_path}, size: {file_size}")

                    if file_size > app.config['MAX_CONTENT_LENGTH']:
                         flash(f"Le fichier '{filename}' dépasse la taille maximale autorisée.", "error")
                         # Clean up this specific file immediately
                         try: os.remove(temp_path)
                         except OSError: pass
                         newly_uploaded_paths.remove(temp_path)
                         temp_files_to_clean.remove(temp_path)
                         continue # Skip this file

                    # Avoid duplicates if user uploads same file again
                    if not any(f['filename'] == filename for f in uploaded_files_info):
                        uploaded_files_info.append({
                            'filename': filename,
                            'filetype': file.content_type or 'application/octet-stream', # Provide default mimetype
                            'filesize': file_size,
                            'temp_path': temp_path # Store temp path to read later
                        })
                    else:
                         logger.warning(f"Duplicate file upload skipped: {filename}")
                         # Clean up the duplicate temp file
                         try: os.remove(temp_path)
                         except OSError: pass
                         newly_uploaded_paths.remove(temp_path)
                         temp_files_to_clean.remove(temp_path)

                else:
                    flash(f"Type de fichier non autorisé pour '{file.filename}'.", "warning")
            elif file:
                 logger.warning("Received a file object without a filename.")

    except Exception as e:
        logger.error(f"Erreur lors du traitement des fichiers uploadés: {e}", exc_info=True)
        flash("Une erreur s'est produite lors du traitement des fichiers.", "error")
        # Clean up any files just uploaded in this request
        for temp_path in newly_uploaded_paths:
            try: os.remove(temp_path)
            except OSError: pass
        # Don't modify session's temp_files_to_clean list here, let finalize handle it
        return redirect(url_for('documents')) # Go back to documents step

    # Update session data
    booking_data['additional_info'] = additional_info
    booking_data['selected_global_documents'] = selected_global_documents
    booking_data['uploaded_files_info'] = uploaded_files_info
    session['temp_files_to_clean'] = temp_files_to_clean # Update session list

    session['booking_data'] = booking_data
    session['booking_step'] = 5
    logger.info(f"Booking Step 4 completed for {booking_data['email']}. Added {len(newly_uploaded_paths)} new files. Proceeding to confirmation.")


    return render_template('confirmation.html', booking_data=booking_data)


@app.route('/finalize', methods=['POST'])
@check_db_connection
def finalize():
    """Finaliser les réservations"""
    if 'booking_data' not in session or session.get('booking_step', 0) < 5:
        flash('Session invalide ou étape de confirmation non atteinte.', 'error')
        return redirect(url_for('index'))

    booking_data = session['booking_data']
    temp_files_to_clean = session.get('temp_files_to_clean', [])
    final_booking_ids = []
    processed_temp_files = set() # Track files successfully processed
    errors_occurred = False
    email_sending_failed = False

    # Options supplémentaires
    send_confirmation = request.form.get('send_confirmation') == 'on'
    # add_to_calendar option removed from server-side, handled by client JS download

    # --- Transaction Simulation ---
    # In a real scenario with an ORM, you'd use its transaction management.
    # With raw psycopg2, we'll try to commit only if all steps succeed.
    # The db_manager's context manager handles commit/rollback per operation.
    # For multi-step logic like this, a higher-level transaction in app.py is better.
    # We simulate by collecting IDs and processing docs after booking creation.

    try:
        bookings_to_create_data = []
        # 1. Re-verify slot availability for all selected modules first
        logger.info("Re-verifying slot availability before finalization...")
        for module in booking_data['modules']:
            availability = db_manager.check_slot_availability(module['date'], module['hour'], module['minutes'])
            if not availability['available']:
                flash(f"Le créneau pour '{module['formation_name']}' ({module['date']} @ {module['hour']}:{module['minutes']:02d}) n'est plus disponible.", 'error')
                errors_occurred = True
            else:
                 # Prepare data if available
                 bookings_to_create_data.append({
                    'service': booking_data['department'],
                    'contact': booking_data['contact'],
                    'email': booking_data['email'],
                    'phone': booking_data.get('phone'),
                    'formation_id': module['formation_id'],
                    'formation_name': module['formation_name'],
                    'date': module['date'],
                    'hour': module['hour'],
                    'minutes': module['minutes'],
                    'participants': booking_data['participants'],
                    'additional_info': booking_data.get('additional_info'),
                    'status': 'confirmed'
                })

        if errors_occurred:
             raise ValueError("Certains créneaux ne sont plus disponibles.")
        logger.info("Slot availability verified.")

        # 2. Create all bookings
        logger.info(f"Creating {len(bookings_to_create_data)} bookings...")
        for booking_to_create in bookings_to_create_data:
            booking_id = db_manager.create_booking(booking_to_create)
            if not booking_id:
                errors_occurred = True
                logger.error(f"Failed to create booking for {booking_to_create['formation_name']}")
                flash(f"Erreur lors de la création de la réservation pour {booking_to_create['formation_name']}.", "error")
                # If one fails, should we stop? Or try others? Stopping is safer for consistency.
                raise ValueError(f"Failed to create booking for {booking_to_create['formation_name']}")

            final_booking_ids.append(booking_id)
            logger.info(f"Booking {booking_id} created for {booking_to_create['formation_name']}.")

            # 3. Process documents for *this specific booking* right after creation
            logger.info(f"Processing documents for booking {booking_id}...")
            # Uploaded documents
            for doc_info in booking_data.get('uploaded_files_info', []):
                temp_path = doc_info.get('temp_path')
                if temp_path and os.path.exists(temp_path):
                    try:
                        with open(temp_path, 'rb') as f:
                            file_data = f.read()

                        document_data = {
                            'filename': doc_info['filename'],
                            'filetype': doc_info['filetype'],
                            'filesize': doc_info['filesize'],
                            'filedata': psycopg2.Binary(file_data), # Use Binary wrapper
                            'document_type': 'attachment',
                            'description': 'Document ajouté lors de la réservation',
                            'is_global': False,
                            'uploaded_by': booking_data['email']
                        }
                        doc_db_id = db_manager.save_document(document_data)
                        if doc_db_id:
                            assoc_success = db_manager.associate_document_to_booking(doc_db_id, booking_id)
                            if assoc_success:
                                logger.info(f"Document {doc_info['filename']} (ID: {doc_db_id}) saved and associated with booking {booking_id}.")
                                processed_temp_files.add(temp_path) # Mark as processed for cleanup
                            else:
                                logger.error(f"Failed to associate document {doc_db_id} with booking {booking_id}.")
                                errors_occurred = True # Treat association failure as error
                        else:
                             logger.error(f"Failed to save document {doc_info['filename']} to DB.")
                             errors_occurred = True
                             flash(f"Erreur lors de la sauvegarde du document {doc_info['filename']}.", "error")

                    except Exception as doc_err:
                        logger.error(f"Error processing document {doc_info['filename']} for booking {booking_id}: {doc_err}")
                        errors_occurred = True
                        flash(f"Erreur lors du traitement du document {doc_info['filename']}.", "error")
                elif temp_path:
                     logger.warning(f"Temporary file path not found or invalid for processing: {temp_path}")
                     # Don't mark as processed if path was bad
                else:
                     logger.debug("Skipping document info entry without temp_path.")


            # Selected global documents
            for global_doc_id_str in booking_data.get('selected_global_documents', []):
                 try:
                     global_doc_id = int(global_doc_id_str)
                     assoc_success = db_manager.associate_document_to_booking(global_doc_id, booking_id)
                     if assoc_success:
                         logger.info(f"Global document {global_doc_id} associated with booking {booking_id}.")
                     else:
                          logger.warning(f"Failed to associate global document {global_doc_id} to booking {booking_id} (might already exist).")
                 except (ValueError, TypeError):
                     logger.warning(f"Invalid global document ID found: {global_doc_id_str}")
                 except Exception as assoc_err:
                     logger.error(f"Error associating global document {global_doc_id_str} to booking {booking_id}: {assoc_err}")
                     # Decide if this is critical - maybe not, log and continue

            # If any document error occurred for this booking, stop the whole process
            if errors_occurred:
                 raise ValueError("Erreur lors du traitement des documents pour une réservation.")

        # If loop completes without errors_occurred being True
        logger.info(f"All bookings ({len(final_booking_ids)}) and documents processed successfully for {booking_data['email']}.")

        # 4. Send confirmation emails AFTER successful processing
        if send_confirmation and final_booking_ids:
            logger.info(f"Sending confirmation emails for {len(final_booking_ids)} bookings to {booking_data['email']}...")
            for bk_id in final_booking_ids:
                try:
                    full_booking_details = db_manager.get_booking_by_id(bk_id)
                    if full_booking_details:
                        # Ensure participants are loaded if needed by email template
                        full_booking_details['participants'] = full_booking_details.get('participants', [])
                        send_confirmation_email(full_booking_details)
                    else:
                        logger.warning(f"Could not fetch details for booking {bk_id} to send email.")
                except Exception as mail_err:
                    logger.error(f"Failed to send confirmation email for booking {bk_id}: {mail_err}")
                    email_sending_failed = True # Flag but don't rollback booking

        # 5. Clean up session and redirect
        session.pop('booking_data', None)
        session.pop('booking_step', None)
        session.pop('temp_files_to_clean', None) # Clear the list

        flash('Vos réservations ont été créées avec succès !', 'success')
        if email_sending_failed:
            flash("Certains emails de confirmation n'ont pas pu être envoyés. Veuillez vérifier manuellement.", 'warning')

        session['last_booking_ids'] = final_booking_ids # Store for thank you page

        return redirect(url_for('thank_you'))

    except Exception as e:
        # --- Error Handling ---
        logger.error(f"Erreur lors de la finalisation de la réservation pour {booking_data.get('email', 'N/A')}: {e}", exc_info=True)
        flash(f"Une erreur majeure est survenue lors de la finalisation : {str(e)} Veuillez réessayer ou contacter le support.", 'error')
        # Keep session data for retry? Or clear it? Keeping it might allow retry.
        session['booking_step'] = 5 # Ensure user is back at confirmation
        # Don't clear temp_files_to_clean list from session yet, maybe needed for retry
        return redirect(url_for('confirmation'))

    finally:
        # --- Cleanup Processed Temporary Files ---
        # Clean up only the files that were successfully processed and associated
        logger.debug(f"Attempting cleanup for processed temp files: {processed_temp_files}")
        for temp_path in processed_temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Cleaned up processed temporary file: {temp_path}")
            except OSError as clean_err:
                logger.error(f"Failed to clean up processed temporary file {temp_path}: {clean_err}")

        # Decide what to do with temp_files_to_clean if errors occurred *before* processing them.
        # If the finalize failed early, the list in the session remains, and they won't be in processed_temp_files.
        # Maybe add a periodic cleanup task for old files in the upload folder?


@app.route('/thank-you')
def thank_you():
    """Page de remerciement après finalisation"""
    last_booking_ids = session.get('last_booking_ids', [])
    email = "l'adresse indiquée" # Default
    if last_booking_ids:
         # Fetch email from the first booking created in the last transaction
         first_booking = db_manager.get_booking_by_id(last_booking_ids[0]) if db_manager else None
         if first_booking:
             email = first_booking['email']

    # Clear the last booking IDs from session after use
    session.pop('last_booking_ids', None)

    return render_template('thank_you.html', email=email)


# --- API Routes ---

@app.route('/api/ping', methods=['GET'])
def ping():
    """API pour vérifier la connexion au serveur et à la DB"""
    db_ok = False
    db_error = None
    if db_manager:
        try:
            db_ok = db_manager.ping()
        except Exception as e:
            db_error = str(e)
            logger.error(f"API Ping DB check failed: {db_error}")

    if db_ok:
        return jsonify({"status": "ok", "message": "Serveur et base de données opérationnels."}), 200
    else:
        return jsonify({"status": "error", "message": f"Erreur de connexion à la base de données: {db_error or 'Inconnue'}"}), 503


@app.route('/api/bookings', methods=['GET'])
@check_db_connection
# @login_required # Uncomment if admin only access is needed
def get_bookings():
    """API pour récupérer les réservations (filtrable par département)"""
    department = request.args.get('department')
    try:
        if department:
            bookings = db_manager.get_bookings_by_service(department)
        else:
            bookings = db_manager.get_all_bookings()
        return jsonify(bookings)
    except Exception as e:
        logger.error(f"API Error getting bookings: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la récupération des réservations."}), 500


@app.route('/api/booking/<int:booking_id>', methods=['GET'])
@check_db_connection
# @login_required # Uncomment if admin only access is needed
def get_booking(booking_id):
    """API pour récupérer une réservation par ID"""
    try:
        booking = db_manager.get_booking_by_id(booking_id)
        if booking:
            # Get associated documents metadata
            booking['associated_documents'] = db_manager.get_documents_metadata_by_booking_id(booking_id)
            return jsonify(booking)
        else:
            return jsonify({"error": "Réservation non trouvée"}), 404
    except Exception as e:
        logger.error(f"API Error getting booking {booking_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la récupération de la réservation."}), 500


@app.route('/api/booking/<int:booking_id>', methods=['DELETE'])
@check_db_connection
@login_required # Admin only
def delete_booking_api(booking_id):
    """API pour supprimer une réservation (Admin)"""
    try:
        success = db_manager.delete_booking(booking_id)
        if success:
            return jsonify({"message": "Réservation supprimée avec succès"}), 200
        else:
            # Check if it didn't exist vs other error
            booking_exists = db_manager.get_booking_by_id(booking_id)
            if not booking_exists:
                 return jsonify({"error": "Réservation non trouvée"}), 404
            else:
                 logger.error(f"API delete_booking failed for existing booking {booking_id}")
                 return jsonify({"error": "Erreur lors de la suppression de la réservation"}), 500
    except Exception as e:
        logger.error(f"API Error deleting booking {booking_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la suppression."}), 500


@app.route('/api/calendar_data', methods=['GET'])
@check_db_connection
def get_calendar_data():
    """API pour récupérer les données du calendrier (filtrable)"""
    month_str = request.args.get('month')
    department = request.args.get('department') # Optional filter

    try:
        calendar_data = generate_calendar_data(current_month=month_str, department=department)
        return jsonify(calendar_data)
    except Exception as e:
        logger.error(f"API Error generating calendar data: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la génération du calendrier."}), 500


@app.route('/api/slots', methods=['GET'])
@check_db_connection
def get_available_slots():
    """API pour récupérer les créneaux disponibles pour un mois/formation"""
    month_str = request.args.get('month')
    # formation_id = request.args.get('formation_id') # Filtering by formation not implemented here yet

    if not month_str:
        return jsonify({"error": "Le paramètre 'month' est requis."}), 400

    try:
        month = int(month_str)
        # Determine year based on current date or config if needed
        current_year = datetime.date.today().year
        # Use year from config if available months span years, otherwise assume current/next
        # Simple assumption for now: use 2025 as per AVAILABLE_MONTHS
        year = 2025
        if not (1 <= month <= 12):
            raise ValueError("Mois invalide.")

        num_days = calendar.monthrange(year, month)[1]
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, num_days)

        # Optimize: Fetch only bookings for the relevant month range
        # Add a method to db_manager: get_bookings_for_month(year, month)
        all_bookings = db_manager.get_all_bookings() # Less efficient for many bookings
        booked_slots = set()
        for booking in all_bookings:
             try:
                 booking_date = datetime.datetime.strptime(booking['date'], '%Y-%m-%d').date()
                 if start_date <= booking_date <= end_date:
                     slot_key = (booking['date'], booking['hour'], booking['minutes'])
                     booked_slots.add(slot_key)
             except (ValueError, TypeError):
                 logger.warning(f"Skipping booking {booking.get('id')} due to invalid date format: {booking.get('date')}")
                 continue

        available_slots = []
        current_date = start_date
        from config import BUSINESS_HOURS # Import here or at top
        while current_date <= end_date:
            # Check if it's a weekday (Monday=0 to Sunday=6)
            if current_date.weekday() < 5: # Monday to Friday
                 # Iterate through possible start times based on interval
                 current_time = datetime.datetime.combine(current_date, datetime.time(BUSINESS_HOURS['start'], 0))
                 end_of_day = datetime.datetime.combine(current_date, datetime.time(BUSINESS_HOURS['end'], 0))
                 interval_minutes = BUSINESS_HOURS.get('interval', 30)

                 while current_time < end_of_day:
                     hour = current_time.hour
                     minutes = current_time.minute
                     # Check if this start time allows a 90-min session within business hours
                     session_end_time = current_time + datetime.timedelta(minutes=90)
                     if session_end_time.date() == current_date and session_end_time.time() <= datetime.time(BUSINESS_HOURS['end'], 0):
                         slot_key = (current_date.strftime('%Y-%m-%d'), hour, minutes)
                         is_booked = slot_key in booked_slots

                         available_slots.append({
                             "date": current_date.strftime('%Y-%m-%d'),
                             "weekday": format_date_filter(current_date).split(' ')[0], # Get day name from formatted date
                             "hour": hour,
                             "minute": minutes,
                             "formatted_time": f"{hour:02d}:{minutes:02d}",
                             "available": not is_booked
                         })
                     # Move to the next potential start time
                     current_time += datetime.timedelta(minutes=interval_minutes)

            current_date += datetime.timedelta(days=1)

        return jsonify(available_slots)

    except ValueError as ve:
        return jsonify({"error": f"Paramètre invalide: {ve}"}), 400
    except Exception as e:
        logger.error(f"API Error getting slots: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la récupération des créneaux."}), 500


@app.route('/api/documents/<int:booking_id>', methods=['GET'])
@check_db_connection
# @login_required # Or check if user is participant/contact?
def get_documents_api(booking_id):
    """API pour récupérer les métadonnées des documents d'une réservation"""
    try:
        # Add permission check here if needed
        documents = db_manager.get_documents_metadata_by_booking_id(booking_id)
        return jsonify(documents)
    except Exception as e:
        logger.error(f"API Error getting documents for booking {booking_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de la récupération des documents."}), 500


@app.route('/api/document/<int:document_id>', methods=['GET'])
@check_db_connection
# Add permission check here - is user allowed to download this?
def download_document_api(document_id):
    """API pour télécharger un document (vérifier les permissions !)"""
    try:
        # --- Permission Check Example ---
        is_admin = session.get('admin_logged_in', False)
        user_email = request.args.get('user_email') # Or get from user session if implemented

        document = db_manager.get_document_by_id(document_id)
        if not document or not document.get('filedata'):
            return jsonify({"error": "Document non trouvé ou vide"}), 404

        allowed = False
        if is_admin:
            allowed = True
        elif document['is_global']:
             allowed = True # Allow download of global documents
        elif user_email:
             # Check if user is contact or participant of *any* booking associated with this doc
             associated_bookings = db_manager.get_bookings_for_document(document_id) # Need to implement this in db_manager
             for booking in associated_bookings:
                 if booking['email'] == user_email or any(p.get('email') == user_email for p in booking.get('participants',[])):
                     allowed = True
                     break
        # ---------------------------------

        if not allowed:
             logger.warning(f"Download denied for document {document_id} by user {user_email or 'anonymous'} / admin: {is_admin}")
             return jsonify({"error": "Accès non autorisé"}), 403
        # ---------------------------------

        import io
        return send_file(
            io.BytesIO(document['filedata']),
            as_attachment=True,
            download_name=document['filename'],
            mimetype=document['filetype'] or 'application/octet-stream' # Provide default mimetype
        )
    except Exception as e:
        logger.error(f"API Error downloading document {document_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors du téléchargement."}), 500


@app.route('/api/feedback', methods=['POST'])
@check_db_connection
def send_feedback_api():
    """API pour enregistrer un feedback utilisateur"""
    try:
        # Prefer JSON, fallback to form
        if request.is_json:
            feedback_data = request.get_json()
        else:
            feedback_data = request.form.to_dict()

        message = feedback_data.get('message', '').strip()
        if not message:
            return jsonify({"error": "Le message est requis"}), 400

        feedback_entry = {
            'type': feedback_data.get('type', 'other'),
            'message': message,
            'email': feedback_data.get('email', '').strip() or None # Store None if empty
        }

        feedback_id = db_manager.save_feedback(feedback_entry)
        if feedback_id:
            db_manager.add_activity_log(
                'feedback_submitted',
                {'email': feedback_entry.get('email')},
                {'feedback_id': feedback_id},
                ip_address=get_request_ip()
            )
            return jsonify({"id": feedback_id, "message": "Feedback enregistré avec succès"}), 201
        else:
            logger.error("Failed to save feedback to database.")
            return jsonify({"error": "Impossible d'enregistrer le feedback"}), 500
    except Exception as e:
        logger.error(f"API Error saving feedback: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de l'enregistrement du feedback."}), 500


@app.route('/api/waitlist', methods=['POST'])
@check_db_connection
def add_to_waitlist_api():
    """API pour s'inscrire sur une liste d'attente"""
    data = request.json
    required = ['booking_id', 'service', 'contact', 'email']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Données manquantes pour la liste d'attente (booking_id, service, contact, email requis)."}), 400

    try:
        # Optional: Add check if user is already on waitlist for this booking?
        # Optional: Add check if waitlist is full based on config?
        waitlist_id = db_manager.add_to_waiting_list(data)
        if waitlist_id:
            db_manager.add_activity_log(
                'waitlist_added',
                {'email': data['email'], 'service': data['service']},
                {'booking_id': data['booking_id'], 'waitlist_id': waitlist_id},
                ip_address=get_request_ip()
            )
            return jsonify({"id": waitlist_id, "message": "Inscription à la liste d'attente réussie."}), 201
        else:
            logger.error(f"Failed to add {data['email']} to waitlist for booking {data['booking_id']}")
            return jsonify({"error": "Erreur lors de l'inscription à la liste d'attente."}), 500
    except Exception as e:
        logger.error(f"API Error adding to waitlist: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de l'inscription."}), 500


@app.route('/api/waitlist/<int:waitlist_id>', methods=['DELETE'])
@check_db_connection
# Add permission check - only the user or admin should delete
def remove_from_waitlist_api(waitlist_id):
    """API pour se retirer d'une liste d'attente"""
    try:
        # --- Permission Check ---
        # Example: Fetch waitlist entry, check email against session/param, or check admin status
        # waitlist_entry = db_manager.get_waitlist_entry(waitlist_id) # Need this method in db_manager
        # user_email = session.get('user_email')
        # is_admin = session.get('admin_logged_in')
        # if not (is_admin or (waitlist_entry and waitlist_entry['email'] == user_email)):
        #      return jsonify({"error": "Action non autorisée"}), 403
        # ------------------------

        success = db_manager.remove_from_waitlist(waitlist_id)
        if success:
            db_manager.add_activity_log('waitlist_removed', None, {'waitlist_id': waitlist_id}, ip_address=get_request_ip())
            return jsonify({"message": "Retrait de la liste d'attente réussi."}), 200
        else:
            # Check if it existed before declaring error
            # waitlist_entry = db_manager.get_waitlist_entry(waitlist_id)
            # if not waitlist_entry:
            #      return jsonify({"error": "Entrée non trouvée"}), 404
            # else:
                 logger.error(f"API remove_from_waitlist failed for existing entry {waitlist_id}")
                 return jsonify({"error": "Erreur lors de la suppression."}), 500
    except Exception as e:
        logger.error(f"API Error removing from waitlist {waitlist_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors du retrait."}), 500


@app.route('/api/attendance/<int:booking_id>', methods=['PUT'])
@check_db_connection
@login_required # Admin only
def record_attendance_api(booking_id):
    """API pour enregistrer/màj les présences (Admin)"""
    data = request.json
    # Validate incoming data structure
    if not data or 'attendance' not in data or not isinstance(data['attendance'], list):
         return jsonify({"error": "Format des données de présence invalide."}), 400
    # Assuming date is derived or known, otherwise it should be passed
    booking = db_manager.get_booking_by_id(booking_id)
    if not booking:
         return jsonify({"error": "Réservation non trouvée."}), 404

    try:
        attendance_data = {
            'booking_id': booking_id,
            'date': booking['date'], # Use booking date for attendance date
            'attendance': data['attendance'], # Should be JSON structure [{id:.., name:.., present:.., status:..}, ...]
            'comments': data.get('comments', '').strip() or None,
            'recorded_by': session.get('admin_email', 'admin') # Track who recorded
        }
        attendance_id = db_manager.save_attendance(attendance_data)
        if attendance_id:
            return jsonify({"id": attendance_id, "message": "Présences enregistrées avec succès."}), 200
        else:
            logger.error(f"Failed to save attendance for booking {booking_id}")
            return jsonify({"error": "Erreur lors de l'enregistrement des présences."}), 500
    except Exception as e:
        logger.error(f"API Error recording attendance for booking {booking_id}: {e}", exc_info=True)
        return jsonify({"error": "Erreur serveur lors de l'enregistrement."}), 500


# --- Admin Routes ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Page de connexion admin"""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        password = request.form.get('password')
        ip = get_request_ip()
        # Use check_password_hash against the hash stored in config
        if password and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear() # Prevent session fixation
            session['admin_logged_in'] = True
            session.permanent = True # Make session persistent based on lifetime
            # Store an identifier if needed, e.g., session['admin_user'] = 'admin'
            g.is_admin = True
            flash('Connexion réussie !', 'success')
            # Log admin login
            db_manager.add_activity_log('admin_login_success', {'admin': 'admin'}, None, ip_address=ip)
            next_url = request.args.get('next')
            # Validate next_url to prevent open redirect vulnerability
            if next_url and urljoin(request.host_url, next_url).startswith(request.host_url):
                 return redirect(next_url)
            else:
                 return redirect(url_for('admin_dashboard'))
        else:
            flash('Mot de passe incorrect.', 'error')
            # Log failed attempt
            db_manager.add_activity_log('admin_login_failed', {'admin': 'admin'}, None, ip_address=ip)
            time.sleep(1) # Add a small delay to slow down brute-force attempts

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Déconnexion admin"""
    ip = get_request_ip()
    admin_identifier = session.get('admin_user', 'admin') # Get identifier if stored
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None) # Clear any admin identifier
    session.clear() # Clear the entire session on logout
    g.is_admin = False
    flash('Vous avez été déconnecté.', 'info')
    # Log admin logout
    db_manager.add_activity_log('admin_logout', {'admin': admin_identifier}, None, ip_address=ip)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
@check_db_connection
def admin_dashboard():
    """Tableau de bord admin"""
    try:
        stats = db_manager.get_dashboard_stats()
        # Fetch recent activity logs for the dashboard card
        recent_logs = db_manager.get_activity_logs(limit=5) # Get 5 recent logs
        stats['recent_activity'] = recent_logs # Add to stats dict for template

        return render_template('admin_dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Erreur lors du chargement du tableau de bord admin: {e}", exc_info=True)
        flash('Une erreur est survenue lors du chargement du tableau de bord.', 'error')
        return redirect(url_for('index')) # Or a generic error page

# --- Placeholder Admin Routes ---
# Implement the logic for these routes based on admin_dashboard.html links

@app.route('/admin/bookings')
@login_required
@check_db_connection
def admin_bookings():
    """Page de gestion des sessions (Admin)"""
    try:
        all_bookings = db_manager.get_all_bookings()
        return render_template('admin/bookings_list.html', bookings=all_bookings) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin bookings list: {e}", exc_info=True)
        flash("Erreur lors du chargement de la liste des réservations.", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/participants')
@login_required
@check_db_connection
def admin_participants():
    """Page de gestion des participants (Admin)"""
    try:
        all_bookings = db_manager.get_all_bookings()
        all_participants = []
        seen_emails = set() # To avoid listing same person multiple times if in multiple bookings
        for booking in all_bookings:
            for p in booking.get('participants', []):
                 p_data = p.copy()
                 p_data['booking_id'] = booking['id']
                 p_data['formation_name'] = booking['formation_name']
                 p_data['date'] = booking['date']
                 p_data['service'] = booking['service']
                 p_email = p_data.get('email')
                 # Simple deduplication based on email for this view
                 if not p_email or p_email not in seen_emails:
                     all_participants.append(p_data)
                     if p_email: seen_emails.add(p_email)

        return render_template('admin/participants_list.html', participants=all_participants) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin participants list: {e}", exc_info=True)
        flash("Erreur lors du chargement de la liste des participants.", "error")
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/documents')
@login_required
@check_db_connection
def admin_documents():
    """Page de gestion des documents (Admin)"""
    try:
        all_docs = db_manager.get_all_documents_metadata()
        return render_template('admin/documents_list.html', documents=all_docs) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin documents list: {e}", exc_info=True)
        flash("Erreur lors du chargement de la liste des documents.", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/waitlist')
@login_required
@check_db_connection
def admin_waitlist():
    """Page de gestion de la liste d'attente (Admin)"""
    try:
        waitlist = db_manager.get_waiting_list()
        return render_template('admin/waitlist.html', waitlist=waitlist) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin waitlist: {e}", exc_info=True)
        flash("Erreur lors du chargement de la liste d'attente.", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/logs')
@login_required
@check_db_connection
def admin_logs():
    """Page de consultation des logs d'activité (Admin)"""
    try:
        limit = request.args.get('limit', 200, type=int)
        logs = db_manager.get_activity_logs(limit=limit)
        return render_template('admin/activity_logs.html', logs=logs, limit=limit) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin activity logs: {e}", exc_info=True)
        flash("Erreur lors du chargement des logs d'activité.", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/feedback')
@login_required
@check_db_connection
def admin_feedback():
    """Page de gestion des feedbacks (Admin)"""
    try:
        feedbacks = db_manager.get_all_feedback()
        return render_template('admin/feedback_list.html', feedbacks=feedbacks) # Create this template
    except Exception as e:
        logger.error(f"Error loading admin feedback list: {e}", exc_info=True)
        flash("Erreur lors du chargement des feedbacks.", "error")
        return redirect(url_for('admin_dashboard'))

# Add routes for editing/deleting specific items (e.g., /admin/booking/<id>/edit)
# Example:
# @app.route('/admin/booking/<int:booking_id>/edit', methods=['GET', 'POST'])
# @login_required
# @check_db_connection
# def admin_edit_booking(booking_id):
#     # Fetch booking, handle POST for update, use db_manager.update_booking
#     pass


# --- User Routes ---

@app.route('/user_dashboard')
@check_db_connection
def user_dashboard():
    """Tableau de bord utilisateur"""
    email = request.args.get('email', '').strip().lower()
    is_guest = not bool(email)

    bookings_as_contact = []
    bookings_as_participant = []
    waitlist_entries = []
    global_documents = []
    sorted_bookings = []

    if is_guest:
        flash("Veuillez fournir votre adresse email dans l'URL (?email=votre@email.com) pour voir votre tableau de bord personnel.", "info")
        # Optionally fetch global documents even for guests
        try:
            global_documents = db_manager.get_global_documents()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des documents globaux pour invité: {e}")
    else:
        try:
            bookings_as_contact = db_manager.get_bookings_by_email(email)
            bookings_as_participant = db_manager.get_bookings_by_participant_email(email)
            waitlist_entries = db_manager.get_waitlist_by_email(email)
            global_documents = db_manager.get_global_documents()

            # Combine and deduplicate bookings
            all_user_bookings = {}
            for b in bookings_as_contact:
                b['role'] = 'contact'
                all_user_bookings[b['id']] = b
            for b in bookings_as_participant:
                if b['id'] not in all_user_bookings:
                    b['role'] = 'participant'
                    all_user_bookings[b['id']] = b
                else:
                    # User is both contact and participant
                    all_user_bookings[b['id']]['role'] = 'contact_participant'

            sorted_bookings = sorted(all_user_bookings.values(), key=lambda x: (x.get('date', '9999-12-31'), x.get('hour', 0), x.get('minutes', 0)))

        except Exception as e:
            logger.error(f"Erreur lors du chargement du tableau de bord pour {email}: {e}", exc_info=True)
            flash("Une erreur est survenue lors du chargement de vos informations.", 'error')
            # Keep lists empty on error

    today_date_str = datetime.date.today().strftime('%Y-%m-%d')

    return render_template(
        'user_dashboard.html',
        email=email if not is_guest else None,
        user_bookings=sorted_bookings, # Pass combined list
        bookings_as_contact=bookings_as_contact, # Keep separate lists if template uses them directly
        bookings_as_participant=bookings_as_participant,
        waitlist_entries=waitlist_entries,
        global_documents=global_documents,
        today_date=today_date_str, # Pass as string
        is_guest=is_guest
    )


# --- Export Routes ---

@app.route('/export/ical')
@check_db_connection
def export_ical():
    """Export bookings to iCalendar format"""
    user_email = request.args.get('email', '').strip().lower()
    # provider = request.args.get('provider', 'all') # Not used currently

    if not user_email:
        flash("Adresse email requise pour l'export iCal.", "warning")
        return redirect(request.referrer or url_for('index'))

    try:
        # Fetch bookings for the user
        bookings_contact = db_manager.get_bookings_by_email(user_email)
        bookings_participant = db_manager.get_bookings_by_participant_email(user_email)
        all_bookings_dict = {b['id']: b for b in bookings_contact + bookings_participant}

        if not all_bookings_dict:
            flash("Aucune réservation trouvée à exporter pour cet email.", "info")
            return redirect(url_for('user_dashboard', email=user_email))

        # Structure data for iCal generation
        dummy_booking_data = {
            'modules': [],
            'contact': user_email, # Identify the user
            'email': user_email,
            'participants': [] # Participants list not strictly needed for basic iCal
        }
        for booking in all_bookings_dict.values():
             # Fetch full participant list for the specific booking for attendee list
             full_booking = db_manager.get_booking_by_id(booking['id'])
             participants_for_ical = full_booking.get('participants', []) if full_booking else []

             dummy_booking_data['modules'].append({
                 'formation_id': booking['formation_id'],
                 'formation_name': booking['formation_name'],
                 'date': booking['date'],
                 'hour': booking['hour'],
                 'minutes': booking['minutes'],
                 # Pass necessary details for attendee generation
                 'contact_name_for_ical': booking.get('contact', user_email),
                 'contact_email_for_ical': booking.get('email', user_email),
                 'participants_for_ical': participants_for_ical
             })
             # Update main contact info if we found it in a booking they manage
             if booking.get('email') == user_email and booking.get('contact'):
                 dummy_booking_data['contact'] = booking['contact']


        calendar_file_path = generate_ical_file(dummy_booking_data)

        if calendar_file_path:
            # Use a try-finally block for cleanup
            try:
                response = send_file(
                    calendar_file_path,
                    as_attachment=True,
                    download_name=f'formations-anecoop-{user_email}.ics',
                    mimetype='text/calendar'
                )
                return response
            finally:
                # Clean up the temp file after sending attempt
                try:
                    os.remove(calendar_file_path)
                    logger.info(f"Cleaned up temporary iCal file: {calendar_file_path}")
                except OSError as e:
                    logger.error(f"Error cleaning up iCal file {calendar_file_path}: {e}")
        else:
            flash("Erreur lors de la génération du fichier iCalendar.", "error")
            return redirect(url_for('user_dashboard', email=user_email))

    except Exception as e:
        logger.error(f"Erreur lors de l'export iCal pour {user_email}: {e}", exc_info=True)
        flash("Une erreur est survenue lors de l'export du calendrier.", "error")
        return redirect(url_for('user_dashboard', email=user_email))


# --- Helper Functions ---

def send_confirmation_email(booking_details):
    """Envoie un email de confirmation pour une réservation (Improved)"""
    if not booking_details:
        logger.warning("Tentative d'envoi d'email pour une réservation vide.")
        return

    try:
        department_name = next((d['name'] for d in DEPARTMENTS if d['id'] == booking_details['service']), booking_details['service'])
        date_obj = datetime.datetime.strptime(booking_details['date'], '%Y-%m-%d').date()
        formatted_date = format_date_filter(date_obj) # Use template filter

        hour = booking_details['hour']
        minutes = booking_details['minutes']
        start_dt = datetime.datetime.combine(date_obj, datetime.time(hour, minutes))
        end_dt = start_dt + datetime.timedelta(minutes=90) # Assuming 90 min duration
        time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"

        participants_list_html = "<ul>"
        recipients = {booking_details['email'].lower()} # Use a set, normalize email
        cc_list = []

        participants_data = booking_details.get('participants', [])
        if not isinstance(participants_data, list):
             logger.warning(f"Participants data is not a list for booking {booking_details['id']}. Skipping participant list in email.")
             participants_data = [] # Ensure it's a list

        for p in participants_data:
            # Ensure participant is a dict with 'name'
            if isinstance(p, dict) and 'name' in p:
                participants_list_html += f"<li>{escape(p['name'])}"
                p_email = p.get('email', '').strip().lower()
                if p_email:
                    participants_list_html += f" ({escape(p_email)})"
                    # Add participant to recipients/cc if email exists and different from main contact
                    if p_email != booking_details['email'].lower():
                        if EMAIL_CONFIG['templates']['confirmation'].get('cc_participants', False):
                             cc_list.append(p_email)
                        else:
                             recipients.add(p_email) # Send directly if not CCing
                participants_list_html += "</li>"
            else:
                 logger.warning(f"Invalid participant format in booking {booking_details['id']}: {p}")
        participants_list_html += "</ul>"

        subject = EMAIL_CONFIG['templates']['confirmation']['subject'].format(formation_name=booking_details['formation_name'])

        # Render HTML email template (ensure this template exists)
        try:
            html_body = render_template(
                'email/confirmation.html',
                contact_name=booking_details['contact'],
                formation_name=booking_details['formation_name'],
                formatted_date=formatted_date,
                time_str=time_str,
                department_name=department_name,
                participants_list_html=participants_list_html,
                dashboard_link=url_for('user_dashboard', email=booking_details['email'], _external=True),
                additional_info=booking_details.get('additional_info')
            )
        except Exception as render_err:
             logger.error(f"Error rendering confirmation email template: {render_err}", exc_info=True)
             # Fallback to plain text if template fails
             html_body = f"""
Bonjour {escape(booking_details['contact'])},

Votre réservation pour la formation suivante a été confirmée :

Formation : {escape(booking_details['formation_name'])}
Date : {formatted_date}
Horaire : {time_str}
Département : {escape(department_name)}

Participants :
{participants_list_html}  <!-- Basic HTML list -->

Consultez votre tableau de bord: {url_for('user_dashboard', email=booking_details['email'], _external=True)}

Merci,
{APP_NAME}
"""

        msg = Message(
            subject=subject,
            recipients=list(recipients),
            cc=list(set(cc_list)), # Ensure unique CCs
            html=html_body,
            sender=(APP_NAME, EMAIL_CONFIG['username']) # Use app name as sender name
        )

        # Attach iCalendar file if requested
        if EMAIL_CONFIG['templates']['confirmation'].get('include_calendar', False):
             single_booking_data = {
                 'modules': [{
                     'formation_id': booking_details['formation_id'],
                     'formation_name': booking_details['formation_name'],
                     'date': booking_details['date'],
                     'hour': booking_details['hour'],
                     'minutes': booking_details['minutes']
                 }],
                 'contact': booking_details['contact'],
                 'email': booking_details['email'],
                 'participants': participants_data # Pass the validated list
             }
             ical_path = generate_ical_file(single_booking_data)
             if ical_path:
                 try:
                     with open(ical_path, 'rb') as fp:
                         msg.attach(f"{secure_filename(booking_details['formation_name'])}.ics", "text/calendar", fp.read())
                 finally:
                     try: os.remove(ical_path) # Clean up temp iCal file
                     except OSError as e: logger.error(f"Failed to remove temp iCal file {ical_path}: {e}")

        # Send the email
        mail.send(msg)
        logger.info(f"Email de confirmation envoyé pour la réservation {booking_details['id']} à {', '.join(recipients)} (CC: {', '.join(cc_list)})")

    except Exception as e:
        logger.error(f"Erreur lors de la préparation/envoi de l'email de confirmation pour la réservation {booking_details.get('id', 'N/A')}: {e}", exc_info=True)
        raise # Re-raise to signal failure to the caller


def generate_calendar_data(current_month=None, department=None):
    """Génère les données pour l'affichage du calendrier (Improved)"""
    try:
        # Optimize: Fetch only necessary bookings if month/department provided
        all_bookings = db_manager.get_all_bookings() # Replace with filtered fetch if possible

        calendar_data = []
        target_month = None
        if current_month:
            try: target_month = int(current_month)
            except (ValueError, TypeError): pass

        for booking in all_bookings:
            try:
                date_obj = datetime.datetime.strptime(booking['date'], '%Y-%m-%d').date()

                # Filter by month
                if target_month and date_obj.month != target_month:
                    continue
                # Filter by department
                if department and booking['service'] != department:
                    continue

                start_time = datetime.datetime.combine(date_obj, datetime.time(booking['hour'], booking['minutes']))
                # Calculate end time based on duration (assuming 90 minutes)
                end_time = start_time + datetime.timedelta(minutes=90)

                color = CALENDAR_CONFIG['colors'].get(booking['service'], '#3788d8') # Default color
                department_name = next((d['name'] for d in DEPARTMENTS if d['id'] == booking['service']), booking['service'])

                # Ensure participants is a list
                participants_list = booking.get('participants', [])
                if not isinstance(participants_list, list):
                    participants_list = []

                calendar_data.append({
                    'id': str(booking['id']), # Ensure ID is string for FullCalendar
                    'title': booking['formation_name'],
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'backgroundColor': color,
                    'borderColor': color,
                    'extendedProps': {
                        'service': department_name, # Use formatted name
                        'contact': booking['contact'],
                        'email': booking['email'],
                        'participants': len(participants_list),
                        'booking_id': booking['id'] # Keep original ID if needed
                    }
                })
            except Exception as item_err:
                 logger.warning(f"Skipping booking ID {booking.get('id')} in calendar due to processing error: {item_err}")
                 continue # Skip problematic booking

        return calendar_data
    except Exception as e:
        logger.error(f"Erreur lors de la génération des données du calendrier: {e}", exc_info=True)
        return [] # Return empty list on error


def generate_ical_file(booking_data):
    """Génère un fichier iCalendar pour les réservations (Improved)"""
    try:
        from icalendar import Calendar, Event, vText, vCalAddress, vUri
        from datetime import timedelta
        import uuid

        cal = Calendar()
        cal.add('prodid', f'-//{APP_AUTHOR}//{APP_NAME}//FR')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH') # Suitable for downloading

        # Organizer info - use the main contact of the booking data passed
        organizer_email = booking_data.get('email', EMAIL_CONFIG['username'])
        organizer_name = booking_data.get('contact', APP_NAME)
        organizer_cal = vCalAddress(f'MAILTO:{organizer_email}')
        organizer_cal.params['cn'] = vText(organizer_name)

        for module in booking_data['modules']:
            event = Event()
            event.add('summary', module['formation_name'])
            event.add('uid', f"{uuid.uuid4()}@{request.host}") # Unique ID per event
            event.add('dtstamp', datetime.datetime.now(datetime.timezone.utc))

            start_dt = datetime.datetime.strptime(module['date'], '%Y-%m-%d')
            start_dt = start_dt.replace(hour=module['hour'], minute=module['minutes'])
            # Assuming duration is 90 minutes
            end_dt = start_dt + timedelta(minutes=90)

            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)

            # Description
            desc = f"Formation Anecoop: {module['formation_name']}\n"
            desc += f"Responsable: {booking_data['contact']} ({booking_data['email']})\n"
            # Use participants specific to this module if available, else use main list
            participants_for_event = module.get('participants_for_ical', booking_data.get('participants', []))
            if participants_for_event:
                 desc += f"Participants ({len(participants_for_event)}):\n"
                 desc += "\n".join([f"- {p['name']}" for p in participants_for_event if isinstance(p, dict) and 'name' in p])
            event.add('description', desc)

            event.add('location', 'Anecoop (sur site)')
            event.add('status', 'CONFIRMED')
            event.add('organizer', organizer_cal)

            # Add attendees (optional but good practice)
            # Main contact (responsible)
            contact_email_for_event = module.get('contact_email_for_ical', booking_data["email"])
            contact_name_for_event = module.get('contact_name_for_ical', booking_data["contact"])
            attendee_contact = vCalAddress(f'MAILTO:{contact_email_for_event}')
            attendee_contact.params['cn'] = vText(contact_name_for_event)
            attendee_contact.params['role'] = vText('REQ-PARTICIPANT')
            attendee_contact.params['partstat'] = vText('ACCEPTED')
            attendee_contact.params['rsvp'] = vText('FALSE')
            event.add('attendee', attendee_contact, encode=0)

            # Other participants
            for participant in participants_for_event:
                if isinstance(participant, dict) and participant.get('email') and participant['email'] != contact_email_for_event:
                    attendee = vCalAddress(f'MAILTO:{participant["email"]}')
                    attendee.params['cn'] = vText(participant.get('name', participant['email']))
                    attendee.params['role'] = vText('REQ-PARTICIPANT')
                    attendee.params['partstat'] = vText('NEEDS-ACTION')
                    attendee.params['rsvp'] = vText('TRUE')
                    event.add('attendee', attendee, encode=0)

            cal.add_component(event)

        # Save to a temporary file using mkstemp for unique name
        fd, temp_path = tempfile.mkstemp(suffix='.ics', prefix='anecoop_cal_', dir=app.config['UPLOAD_FOLDER'])
        try:
            with os.fdopen(fd, 'wb') as f: # Open in binary mode
                f.write(cal.to_ical())
            logger.info(f"Generated iCalendar file at: {temp_path}")
            return temp_path
        except Exception:
            os.remove(temp_path) # Clean up if writing fails
            raise # Re-raise the writing error

    except ImportError:
         logger.error("La bibliothèque 'icalendar' est nécessaire pour générer des fichiers iCal. Installez-la avec 'pip install icalendar'.")
         return None
    except Exception as e:
        logger.error(f"Erreur lors de la génération du fichier iCalendar: {e}", exc_info=True)
        return None


# --- Main Execution ---
if __name__ == '__main__':
    # Assurez-vous que cette ligne est au niveau 0 (pas d'indentation)

    # Les lignes suivantes sont indentées de 4 espaces
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    if db_manager is None:
        # Les lignes suivantes sont indentées de 8 espaces
        print("CRITICAL: Database initialization failed. Application cannot run.", file=sys.stderr)
        sys.exit(1)

    # Cette ligne est de nouveau indentée de 4 espaces
    app.run(debug=DEBUG, host='0.0.0.0', port=5000, threaded=True)

# Assurez-vous qu'il n'y a pas d'espaces ou de tabulations après la dernière ligne.