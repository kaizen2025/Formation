# File: utils.py
import datetime
import os
import tempfile
import uuid
import json # Pour l'ajout au log
from markupsafe import escape
from flask import current_app, render_template, url_for, request # request ajouté pour IP/UserAgent
from flask_mail import Message
from icalendar import Calendar, Event, vText, vCalAddress
# Importer depuis le projet local
from extensions import mail # Utiliser l'instance Mail de l'app
from db_manager import db_manager # Pour récupérer infos si besoin
from config import ALLOWED_EXTENSIONS, APP_NAME, EMAIL_CONFIG # Importer constantes
# Attention aux imports circulaires si utils importe des choses de app.py
# Flask-Login n'est pas directement utilisé ici, mais on peut vérifier current_user
from flask_login import current_user

# --- Formatting Filters ---
def format_date_filter(date_input):
    if not date_input: return ""
    try:
        if isinstance(date_input, datetime.datetime): date_obj = date_input.date()
        elif isinstance(date_input, datetime.date): date_obj = date_input
        else: date_obj = datetime.date.fromisoformat(str(date_input))
        return date_obj.strftime('%d %B %Y') # Format simple FR
    except (ValueError, TypeError) as e:
        current_app.logger.warning(f"Could not format date '{date_input}': {e}")
        return str(date_input)

def format_datetime_filter(datetime_input):
    if not datetime_input: return ""
    try:
        if isinstance(datetime_input, datetime.datetime): date_obj = datetime_input
        elif isinstance(datetime_input, datetime.date): date_obj = datetime.datetime.combine(datetime_input, datetime.time(0, 0))
        else: date_obj = datetime.datetime.fromisoformat(str(datetime_input).replace('Z', '+00:00'))
        return date_obj.strftime('%d %B %Y à %H:%M') # Format simple FR
    except (ValueError, TypeError) as e:
        current_app.logger.warning(f"Could not format datetime '{datetime_input}': {e}")
        return str(datetime_input)

def filesizeformat_filter(size_bytes):
    if size_bytes is None: return "0 o"
    try:
        size = int(size_bytes)
        if size < 0: return "0 o"
        if size < 1024: return f"{size} o"
        if size < 1024**2: return f"{size/1024:.1f} Ko"
        if size < 1024**3: return f"{size/(1024**2):.1f} Mo"
        return f"{size/(1024**3):.1f} Go"
    except (ValueError, TypeError):
        current_app.logger.warning(f"Could not format file size '{size_bytes}'")
        return "N/A"

def nl2br_filter(text):
    if not text: return ""
    return escape(str(text)).replace('\n', '<br>\n')

# --- Email Sending ---
def send_email(subject, recipients, text_body, html_body, sender=None, attachments=None, cc=None, bcc=None):
    """Generic email sending function."""
    if not mail.app:
        current_app.logger.error("Flask-Mail not initialized correctly.")
        return False
    if not sender:
        sender = (current_app.config.get('APP_NAME', 'Anecoop'), current_app.config['MAIL_USERNAME'])
    msg = Message(subject, sender=sender, recipients=recipients, cc=cc, bcc=bcc)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            # attachment = (filename, content_type, data)
            msg.attach(*attachment)
    try:
        mail.send(msg)
        current_app.logger.info(f"Email sent: '{subject}' to {recipients}")
        return True
    except Exception as e:
        current_app.logger.error(f"Email sending failed: '{subject}' to {recipients}: {e}", exc_info=True)
        return False

def send_session_confirmation_email(session_id):
    """Sends confirmation email for a specific session."""
    if not db_manager: return False
    session_obj = db_manager.get_session_by_id(session_id) # Récupère session + participants + docs
    if not session_obj:
        current_app.logger.error(f"Confirmation Email: Session ID {session_id} not found.")
        return False

    group = session_obj # get_session_by_id inclut les infos groupe
    module = session_obj # et les infos module
    participants = session_obj.get('participants', [])

    # Construire la liste des destinataires
    recipients = set()
    if group.get('contact_email'): recipients.add(group['contact_email'])
    cc_list = set()
    send_to_participants = EMAIL_CONFIG['templates']['confirmation'].get('cc_participants', False)

    participants_list_html = "<ul>"
    for p in participants:
        if p.get('email'):
            if send_to_participants:
                cc_list.add(p['email'])
            else:
                recipients.add(p['email']) # Envoyer directement si pas en CC
        participants_list_html += f"<li>{escape(p['name'])} ({escape(p.get('email', 'email non fourni'))})</li>"
    participants_list_html += "</ul>"
    # S'assurer que le contact principal n'est pas en double dans CC
    if group.get('contact_email') in cc_list:
        cc_list.remove(group['contact_email'])

    subject = EMAIL_CONFIG['templates']['confirmation']['subject'].format(formation_name=module['module_name'])
    # Générer lien sécurisé pour le tableau de bord (si applicable)
    # Note: la route 'user.dashboard_for_group' n'existe pas, on utilise le token
    dashboard_link = url_for('request_user_dashboard_link', _external=True) # Lien vers la page de demande

    # Rendre les templates email (créer email/session_confirmation.html/.txt)
    try:
        html_body = render_template('email/session_confirmation.html',
                                    session=session_obj, group=group, module=module,
                                    participants_list_html=participants_list_html,
                                    dashboard_link=dashboard_link)
        text_body = render_template('email/session_confirmation.txt', # Créer ce template texte aussi
                                    session=session_obj, group=group, module=module,
                                    participants_list_html=participants_list_html, # Adapter pour texte
                                    dashboard_link=dashboard_link)
    except Exception as render_err:
        current_app.logger.error(f"Erreur rendu template email confirmation: {render_err}")
        # Fallback simple texte
        html_body = f"<p>Votre réservation pour {module['module_name']} le {session_obj['session_date']} est confirmée.</p>"
        text_body = f"Votre réservation pour {module['module_name']} le {session_obj['session_date']} est confirmée."


    # Générer et attacher iCal
    attachments = []
    if EMAIL_CONFIG['templates']['confirmation'].get('include_calendar', False):
        ical_path = generate_session_ical(session_obj) # Utiliser la fonction iCal ci-dessous
        if ical_path:
            try:
                with open(ical_path, 'rb') as fp:
                    attachments.append((f"{module['module_code']}_session.ics", "text/calendar", fp.read()))
            except IOError as e: current_app.logger.error(f"Erreur lecture iCal {ical_path}: {e}")
            finally:
                if os.path.exists(ical_path):
                    try: os.remove(ical_path)
                    except OSError as e: current_app.logger.error(f"Erreur suppression iCal {ical_path}: {e}")

    # Envoyer
    success = send_email(subject, list(recipients), text_body, html_body, attachments=attachments, cc=list(cc_list))
    log_details = {'session_id': session_id, 'recipients': list(recipients), 'cc': list(cc_list)}
    if success:
        add_activity_log_wrapper('confirmation_email_sent', details=log_details)
        return True
    else:
        add_activity_log_wrapper('confirmation_email_failed', details=log_details)
        return False

def send_dashboard_link_email(email: str, token: str):
    """Envoie l'email contenant le lien tokenisé vers le tableau de bord."""
    dashboard_url = url_for('user_dashboard', token=token, _external=True)
    subject = EMAIL_CONFIG['templates']['user_dashboard_link']['subject']
    # Créer les templates email/user_dashboard_link.html/.txt
    try:
        html_body = render_template('email/user_dashboard_link.html', dashboard_url=dashboard_url)
        text_body = render_template('email/user_dashboard_link.txt', dashboard_url=dashboard_url)
    except Exception as render_err:
        current_app.logger.error(f"Erreur rendu template email dashboard link: {render_err}")
        html_body = f"<p>Cliquez sur ce lien pour accéder à votre tableau de bord : <a href='{dashboard_url}'>{dashboard_url}</a></p><p>Ce lien expire dans 1 heure.</p>"
        text_body = f"Cliquez sur ce lien pour accéder à votre tableau de bord : {dashboard_url}\nCe lien expire dans 1 heure."

    success = send_email(subject, [email], text_body, html_body)
    log_details = {'recipient': email}
    if success:
         add_activity_log_wrapper('dashboard_link_sent', details=log_details)
    else:
         add_activity_log_wrapper('dashboard_link_failed', details=log_details)
    return success


# --- iCalendar Generation ---
def generate_session_ical(session_obj):
    """Generates an iCalendar file for a single Session dictionary."""
    try:
        cal = Calendar()
        cal.add('prodid', f'-//{current_app.config["APP_AUTHOR"]}//{APP_NAME}//FR')
        cal.add('version', '2.0'); cal.add('calscale', 'GREGORIAN'); cal.add('method', 'PUBLISH')

        event = Event()
        module_name = session_obj.get('module_name', 'Formation')
        group_name = session_obj.get('group_name', 'Groupe Inconnu')
        event.add('summary', f"{module_name} ({group_name})")
        event.add('uid', f"{uuid.uuid4()}@{request.host if request else 'anecoop.local'}")
        event.add('dtstamp', datetime.datetime.now(datetime.timezone.utc))

        start_dt = datetime.datetime.combine(datetime.date.fromisoformat(session_obj['session_date']),
                                           datetime.time(session_obj['start_hour'], session_obj['start_minutes']))
        duration = session_obj.get('duration_minutes', 90)
        end_dt = start_dt + datetime.timedelta(minutes=duration)

        event.add('dtstart', start_dt); event.add('dtend', end_dt)

        desc = f"Formation Anecoop: {module_name}\n"
        desc += f"Groupe: {group_name}\n"
        contact_name = session_obj.get('group_contact', 'N/A')
        contact_email = session_obj.get('group_email', 'N/A')
        desc += f"Responsable: {contact_name} ({contact_email})\n"
        participants = session_obj.get('participants', [])
        if participants:
             desc += f"Participants ({len(participants)}):\n"
             desc += "\n".join([f"- {p.get('name', 'N/A')}" for p in participants])
        event.add('description', desc)
        event.add('location', session_obj.get('location', 'Sur site'))
        status = 'CONFIRMED' if session_obj.get('status') == 'confirmed' else 'CANCELLED'
        event.add('status', status)

        # Organizer
        org_email = EMAIL_CONFIG.get('username', 'system@anecoop.local')
        organizer_cal = vCalAddress(f'MAILTO:{org_email}')
        organizer_cal.params['cn'] = vText(APP_NAME)
        event.add('organizer', organizer_cal)

        # Attendees
        if contact_email != 'N/A':
            attendee_contact = vCalAddress(f'MAILTO:{contact_email}')
            attendee_contact.params['cn'] = vText(contact_name)
            attendee_contact.params['role'] = vText('REQ-PARTICIPANT')
            attendee_contact.params['partstat'] = vText('ACCEPTED' if status == 'CONFIRMED' else 'DECLINED')
            attendee_contact.params['rsvp'] = vText('FALSE')
            event.add('attendee', attendee_contact, encode=0)

        for p in participants:
             p_email = p.get('email')
             if p_email and p_email != contact_email:
                 attendee = vCalAddress(f'MAILTO:{p_email}')
                 attendee.params['cn'] = vText(p.get('name', p_email))
                 attendee.params['role'] = vText('REQ-PARTICIPANT')
                 attendee.params['partstat'] = vText('NEEDS-ACTION')
                 attendee.params['rsvp'] = vText('TRUE')
                 event.add('attendee', attendee, encode=0)

        cal.add_component(event)

        # Save to temp file
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        os.makedirs(upload_folder, exist_ok=True) # Ensure folder exists
        fd, temp_path = tempfile.mkstemp(suffix='.ics', prefix='anecoop_cal_', dir=upload_folder)
        with os.fdopen(fd, 'wb') as f: f.write(cal.to_ical())
        current_app.logger.info(f"Generated iCalendar file at: {temp_path}")
        return temp_path

    except ImportError: current_app.logger.error("Lib 'icalendar' non trouvée."); return None
    except Exception as e: current_app.logger.error(f"Erreur génération iCal: {e}", exc_info=True); return None

# --- Activity Logging Wrapper ---
def add_activity_log_wrapper(action: str, user_info: Optional[Dict]=None, details: Optional[Dict]=None, entity_type: Optional[str]=None, entity_id: Optional[int]=None):
     """ Wrapper pour ajouter un log d'activité facilement """
     if not db_manager: return

     log_user_info = {}
     ip_address = None
     user_agent = None

     # Check if we are in a request context
     if request:
         ip_address = get_request_ip() # Use helper to get IP
         user_agent = request.user_agent.string if request.user_agent else None
         # Check Flask-Login user
         if current_user and current_user.is_authenticated:
             log_user_info = {'admin_id': current_user.id, 'username': current_user.username}
         elif user_info: # Use provided info if no logged-in user
             log_user_info = user_info
     elif user_info: # Use provided info if outside request context
         log_user_info = user_info

     db_manager.add_activity_log(
         action=action,
         user_info=log_user_info or None, # Ensure None if empty
         details=details,
         entity_type=entity_type,
         entity_id=entity_id,
         ip_address=ip_address,
         user_agent=user_agent
     )

# --- Other Utilities ---
def allowed_file(filename):
    """Checks if the file extension is allowed based on config."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_request_ip():
    """Get user IP address from request (if in request context)."""
    if not request: return None
    if request.headers.getlist("X-Forwarded-For"):
       ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.remote_addr:
       ip = request.remote_addr
    else: ip = "Unknown"
    return ip
