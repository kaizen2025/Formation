"""
Application principale pour le système de réservation des formations Anecoop
"""

import os
import json
import logging
import calendar
import datetime
from typing import Dict, List, Any, Tuple
from functools import wraps
from urllib.parse import urljoin

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2.extras

from config import (DATABASE_URL, FORMATION_NAMES, SERVICES, MIN_PARTICIPANTS, MAX_PARTICIPANTS,
                    AVAILABLE_MONTHS, EMAIL_CONFIG, ADMIN_PASSWORD, APP_NAME)
from db_manager import db_manager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Pour les sessions

# Configuration du dossier pour les uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Types de fichiers autorisés
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'
}

# Configuration de l'envoi d'emails
app.config['MAIL_SERVER'] = EMAIL_CONFIG['smtp_server']
app.config['MAIL_PORT'] = EMAIL_CONFIG['smtp_port']
app.config['MAIL_USERNAME'] = EMAIL_CONFIG['username']
app.config['MAIL_PASSWORD'] = EMAIL_CONFIG['password']
app.config['MAIL_USE_TLS'] = EMAIL_CONFIG['use_tls']
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)


def login_required(f):
    """Décorateur pour exiger l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            flash('Veuillez vous connecter pour accéder à cette page', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    """Vérifie si le type de fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', 
                           services=SERVICES,
                           app_name=APP_NAME)


@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """API pour récupérer toutes les réservations"""
    service = request.args.get('service')
    
    if service:
        bookings = db_manager.get_bookings_by_service(service)
    else:
        bookings = db_manager.get_all_bookings()
    
    return jsonify(bookings)


@app.route('/api/booking/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """API pour récupérer une réservation par ID"""
    booking = db_manager.get_booking_by_id(booking_id)
    
    if booking:
        return jsonify(booking)
    else:
        return jsonify({"error": "Réservation non trouvée"}), 404


@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """API pour créer une nouvelle réservation"""
    data = request.json
    
    # Validation des données
    required_fields = ['service', 'contact', 'email', 'formation_id', 'formation_name', 'date', 'hour', 'minutes']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Le champ '{field}' est requis"}), 400
    
    # Vérifier la disponibilité du créneau
    availability = db_manager.check_slot_availability(data['date'], data['hour'], data['minutes'])
    if not availability['available']:
        return jsonify({"error": "Ce créneau est déjà réservé", "details": availability}), 409
    
    # Créer la réservation
    booking_id = db_manager.create_booking(data)
    
    if booking_id:
        # Envoyer un email de confirmation si demandé
        if data.get('send_confirmation', False) and data.get('email'):
            try:
                send_confirmation_email(data)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email de confirmation: {e}")
        
        return jsonify({"id": booking_id, "message": "Réservation créée avec succès"})
    else:
        return jsonify({"error": "Erreur lors de la création de la réservation"}), 500


@app.route('/api/booking/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """API pour mettre à jour une réservation"""
    data = request.json
    
    # Vérifier si la réservation existe
    booking = db_manager.get_booking_by_id(booking_id)
    if not booking:
        return jsonify({"error": "Réservation non trouvée"}), 404
    
    # Validation des données
    required_fields = ['service', 'contact', 'email', 'formation_id', 'formation_name', 'date', 'hour', 'minutes']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Le champ '{field}' est requis"}), 400
    
    # Vérifier si le créneau est toujours disponible (si changé)
    if (data['date'] != booking['date'] or 
        data['hour'] != booking['hour'] or 
        data['minutes'] != booking['minutes']):
        
        availability = db_manager.check_slot_availability(data['date'], data['hour'], data['minutes'])
        if not availability['available']:
            return jsonify({"error": "Ce créneau est déjà réservé", "details": availability}), 409
    
    # Mettre à jour la réservation
    success = db_manager.update_booking(booking_id, data)
    
    if success:
        return jsonify({"message": "Réservation mise à jour avec succès"})
    else:
        return jsonify({"error": "Erreur lors de la mise à jour de la réservation"}), 500


@app.route('/api/booking/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """API pour supprimer une réservation"""
    # Vérifier si la réservation existe
    booking = db_manager.get_booking_by_id(booking_id)
    if not booking:
        return jsonify({"error": "Réservation non trouvée"}), 404
    
    # Supprimer la réservation
    success = db_manager.delete_booking(booking_id)
    
    if success:
        return jsonify({"message": "Réservation supprimée avec succès"})
    else:
        return jsonify({"error": "Erreur lors de la suppression de la réservation"}), 500


@app.route('/api/availability', methods=['GET'])
def check_availability():
    """API pour vérifier la disponibilité d'un créneau"""
    date = request.args.get('date')
    hour = request.args.get('hour')
    minutes = request.args.get('minutes')
    
    if not date or hour is None or minutes is None:
        return jsonify({"error": "Date, heure et minutes sont requis"}), 400
    
    try:
        hour = int(hour)
        minutes = int(minutes)
    except ValueError:
        return jsonify({"error": "L'heure et les minutes doivent être des nombres"}), 400
    
    availability = db_manager.check_slot_availability(date, hour, minutes)
    return jsonify(availability)


@app.route('/api/waitlist', methods=['POST'])
def add_to_waitlist():
    """API pour ajouter quelqu'un à la liste d'attente"""
    data = request.json
    
    # Validation des données
    required_fields = ['booking_id', 'service', 'contact', 'email']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Le champ '{field}' est requis"}), 400
    
    # Vérifier si la réservation existe
    booking = db_manager.get_booking_by_id(data['booking_id'])
    if not booking:
        return jsonify({"error": "Réservation non trouvée"}), 404
    
    # Ajouter à la liste d'attente
    waitlist_id = db_manager.add_to_waiting_list(data)
    
    if waitlist_id:
        return jsonify({"id": waitlist_id, "message": "Ajouté à la liste d'attente avec succès"})
    else:
        return jsonify({"error": "Erreur lors de l'ajout à la liste d'attente"}), 500


@app.route('/api/waitlist', methods=['GET'])
def get_waitlist():
    """API pour récupérer la liste d'attente"""
    waitlist = db_manager.get_waiting_list()
    return jsonify(waitlist)


@app.route('/api/feedback', methods=['POST'])
def send_feedback():
    """API pour envoyer un feedback"""
    data = request.json
    
    # Validation des données
    if 'type' not in data or 'message' not in data:
        return jsonify({"error": "Type et message sont requis"}), 400
    
    # Enregistrer le feedback
    feedback_id = db_manager.save_feedback(data)
    
    if feedback_id:
        return jsonify({"id": feedback_id, "message": "Feedback enregistré avec succès"})
    else:
        return jsonify({"error": "Erreur lors de l'enregistrement du feedback"}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API pour télécharger un fichier"""
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400
    
    file = request.files['file']
    booking_id = request.form.get('booking_id')
    
    if not booking_id:
        return jsonify({"error": "L'ID de réservation est requis"}), 400
    
    if file.filename == '':
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Enregistrer les informations dans la base de données
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        document_data = {
            'booking_id': int(booking_id),
            'filename': filename,
            'filetype': file.content_type,
            'filesize': os.path.getsize(file_path),
            'filedata': psycopg2.Binary(file_data)
        }
        
        document_id = db_manager.save_document(document_data)
        
        # Supprimer le fichier temporaire
        os.remove(file_path)
        
        if document_id:
            return jsonify({
                "id": document_id,
                "filename": filename,
                "filetype": file.content_type,
                "filesize": document_data['filesize'],
                "message": "Fichier téléchargé avec succès"
            })
        else:
            return jsonify({"error": "Erreur lors de l'enregistrement du document"}), 500
    
    return jsonify({"error": "Type de fichier non autorisé"}), 400


@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """API pour récupérer les statistiques du tableau de bord"""
    stats = db_manager.get_dashboard_stats()
    return jsonify(stats)


@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    """API pour récupérer les logs d'activité"""
    limit = request.args.get('limit', 100)
    try:
        limit = int(limit)
    except ValueError:
        limit = 100
    
    logs = db_manager.get_activity_logs(limit)
    return jsonify(logs)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Page de connexion admin"""
    if request.method == 'POST':
        password = request.form.get('password')
        
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Connexion réussie', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Mot de passe incorrect', 'error')
    
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Déconnexion admin"""
    session.pop('admin_logged_in', None)
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_dashboard():
    """Tableau de bord admin"""
    stats = db_manager.get_dashboard_stats()
    return render_template('admin_dashboard.html', stats=stats)


@app.route('/admin/bookings')
@login_required
def admin_bookings():
    """Gestion des réservations (admin)"""
    bookings = db_manager.get_all_bookings()
    return render_template('admin_bookings.html', bookings=bookings)


@app.route('/admin/participants')
@login_required
def admin_participants():
    """Gestion des participants (admin)"""
    bookings = db_manager.get_all_bookings()
    participants = []
    
    for booking in bookings:
        service_name = next((s['name'] for s in SERVICES if s['id'] == booking['service']), booking['service'])
        for participant in booking['participants']:
            participants.append({
                'name': participant['name'],
                'email': participant.get('email', ''),
                'department': participant.get('department', ''),
                'booking_id': booking['id'],
                'service': service_name,
                'formation': booking['formation_name'],
                'date': booking['date']
            })
    
    return render_template('admin_participants.html', participants=participants)


@app.route('/admin/waitlist')
@login_required
def admin_waitlist():
    """Gestion de la liste d'attente (admin)"""
    waitlist = db_manager.get_waiting_list()
    return render_template('admin_waitlist.html', waitlist=waitlist)


@app.route('/admin/logs')
@login_required
def admin_logs():
    """Visualisation des logs (admin)"""
    logs = db_manager.get_activity_logs()
    return render_template('admin_logs.html', logs=logs)


def send_confirmation_email(booking_data):
    """Envoie un email de confirmation pour une réservation"""
    service_name = next((s['name'] for s in SERVICES if s['id'] == booking_data['service']), booking_data['service'])
    
    # Format de la date
    date_obj = datetime.datetime.strptime(booking_data['date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d %B %Y')
    
    # Format de l'heure
    hour = booking_data['hour']
    minutes = booking_data['minutes']
    hour_end = hour + 1
    minutes_end = minutes + 30
    if minutes_end >= 60:
        hour_end += 1
        minutes_end -= 60
    
    time_str = f"{hour:02d}:{minutes:02d} - {hour_end:02d}:{minutes_end:02d}"
    
    # Participants
    participants_list = ""
    for participant in booking_data.get('participants', []):
        participants_list += f"- {participant['name']}"
        if participant.get('email'):
            participants_list += f" ({participant['email']})"
        participants_list += "\n"
    
    # Construire le sujet et le corps de l'email
    subject = f"Confirmation de réservation - Formation {booking_data['formation_name']}"
    
    body = f"""
Bonjour {booking_data['contact']},

Votre réservation pour la formation suivante a été confirmée :

Formation : {booking_data['formation_name']}
Date : {formatted_date}
Horaire : {time_str}
Service : {service_name}

Participants :
{participants_list}

Merci de votre confiance.
L'équipe Anecoop
"""
    
    # Envoyer l'email
    msg = Message(
        subject=subject,
        recipients=[booking_data['email']],
        body=body,
        sender=app.config['MAIL_USERNAME']
    )
    
    # Ajouter en copie les participants qui ont une adresse email
    for participant in booking_data.get('participants', []):
        if participant.get('email') and participant['email'] != booking_data['email']:
            msg.cc.append(participant['email'])
    
    mail.send(msg)


def generate_calendar_data():
    """Génère les données pour l'affichage du calendrier"""
    all_bookings = db_manager.get_all_bookings()
    
    calendar_data = []
    for booking in all_bookings:
        date_obj = datetime.datetime.strptime(booking['date'], '%Y-%m-%d')
        start_time = datetime.datetime(
            date_obj.year, date_obj.month, date_obj.day,
            booking['hour'], booking['minutes']
        )
        end_time = datetime.datetime(
            date_obj.year, date_obj.month, date_obj.day,
            booking['hour'] + 1, booking['minutes'] + 30
        )
        
        # Ajuster si cela dépasse 60 minutes
        if end_time.minute >= 60:
            end_time = end_time.replace(hour=end_time.hour + 1, minute=end_time.minute - 60)
        
        # Couleur selon le service
        colors = {
            'commerce-1': '#2c6ecb',
            'commerce-2': '#2c6ecb',
            'comptabilite': '#e67e22',
            'rh-qualite-marketing': '#2ecc71',
        }
        
        color = colors.get(booking['service'], '#3788d8')
        
        service_name = next((s['name'] for s in SERVICES if s['id'] == booking['service']), booking['service'])
        
        calendar_data.append({
            'id': booking['id'],
            'title': booking['formation_name'],
            'start': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'service': service_name,
                'contact': booking['contact'],
                'email': booking['email'],
                'participants': len(booking['participants'])
            }
        })
    
    return calendar_data


@app.route('/formations', methods=['GET'])
def formations():
    """Page de sélection des formations"""
    service = request.args.get('service')
    contact = request.args.get('contact')
    email = request.args.get('email')
    phone = request.args.get('phone')
    
    if not service or not contact or not email:
        flash('Veuillez remplir tous les champs obligatoires', 'error')
        return redirect(url_for('index'))
    
    # Récupérer le nom du service
    service_name = next((s['name'] for s in SERVICES if s['id'] == service), service)
    
    return render_template(
        'formations.html',
        service=service,
        service_name=service_name,
        contact=contact,
        email=email,
        phone=phone,
        formations=FORMATION_NAMES,
        months=AVAILABLE_MONTHS,
        calendar_data=json.dumps(generate_calendar_data())
    )

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok"}), 200
    
@app.route('/participants', methods=['GET', 'POST'])
def participants():
    """Page de gestion des participants"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        service = request.form.get('service')
        contact = request.form.get('contact')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Récupérer les formations sélectionnées
        formations = []
        for i in range(len(FORMATION_NAMES)):
            formation_id = f"formation{i+1}"
            date = request.form.get(f"date_{formation_id}")
            hour = request.form.get(f"hour_{formation_id}")
            minutes = request.form.get(f"minutes_{formation_id}")
            
            if date and hour and minutes:
                formations.append({
                    'formation_id': formation_id,
                    'formation_name': FORMATION_NAMES[i],
                    'date': date,
                    'hour': int(hour),
                    'minutes': int(minutes)
                })
        
        if len(formations) < len(FORMATION_NAMES):
            flash('Veuillez sélectionner un créneau pour chaque formation', 'error')
            return redirect(url_for('formations', service=service, contact=contact, email=email, phone=phone))
        
        # Stocker les données en session
        session['booking_data'] = {
            'service': service,
            'contact': contact,
            'email': email,
            'phone': phone,
            'formations': formations
        }
        
        return render_template(
            'participants.html',
            service=service,
            contact=contact,
            email=email,
            phone=phone,
            formations=formations,
            min_participants=MIN_PARTICIPANTS,
            max_participants=MAX_PARTICIPANTS
        )
    
    # Si méthode GET, récupérer les données de session
    if 'booking_data' not in session:
        flash('Veuillez commencer par sélectionner un service', 'error')
        return redirect(url_for('index'))
    
    booking_data = session['booking_data']
    
    return render_template(
        'participants.html',
        service=booking_data['service'],
        contact=booking_data['contact'],
        email=booking_data['email'],
        phone=booking_data.get('phone'),
        formations=booking_data['formations'],
        participants=booking_data.get('participants', []),
        min_participants=MIN_PARTICIPANTS,
        max_participants=MAX_PARTICIPANTS
    )


@app.route('/documents', methods=['GET', 'POST'])
def documents():
    """Page de gestion des documents"""
    if request.method == 'POST':
        # Récupérer les données de session
        if 'booking_data' not in session:
            flash('Session expirée. Veuillez recommencer.', 'error')
            return redirect(url_for('index'))
        
        booking_data = session['booking_data']
        
        # Récupérer les participants du formulaire
        participants = []
        participant_count = int(request.form.get('participant_count', 0))
        
        for i in range(participant_count):
            name = request.form.get(f'participant_name_{i}')
            email = request.form.get(f'participant_email_{i}')
            department = request.form.get(f'participant_department_{i}')
            
            if name:  # Le nom est obligatoire
                participants.append({
                    'name': name,
                    'email': email,
                    'department': department
                })
        
        # Vérifier le nombre de participants
        if len(participants) < MIN_PARTICIPANTS:
            flash(f'Vous devez ajouter au moins {MIN_PARTICIPANTS} participants', 'error')
            return redirect(url_for('participants'))
        
        if len(participants) > MAX_PARTICIPANTS:
            flash(f'Vous ne pouvez pas avoir plus de {MAX_PARTICIPANTS} participants', 'error')
            return redirect(url_for('participants'))
        
        # Mettre à jour les données en session
        booking_data['participants'] = participants
        session['booking_data'] = booking_data
        
        return render_template(
            'documents.html',
            booking_data=booking_data,
            allowed_extensions=', '.join(ALLOWED_EXTENSIONS)
        )
    
    # Si méthode GET, récupérer les données de session
    if 'booking_data' not in session:
        flash('Veuillez commencer par sélectionner un service', 'error')
        return redirect(url_for('index'))
    
    booking_data = session['booking_data']
    
    # Vérifier si les participants ont été ajoutés
    if 'participants' not in booking_data or len(booking_data['participants']) < MIN_PARTICIPANTS:
        flash('Veuillez d\'abord ajouter les participants', 'error')
        return redirect(url_for('participants'))
    
    return render_template(
        'documents.html',
        booking_data=booking_data,
        allowed_extensions=', '.join(ALLOWED_EXTENSIONS)
    )


@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    """Page de confirmation finale"""
    if request.method == 'POST':
        # Récupérer les données de session
        if 'booking_data' not in session:
            flash('Session expirée. Veuillez recommencer.', 'error')
            return redirect(url_for('index'))
        
        booking_data = session['booking_data']
        
        # Récupérer les informations supplémentaires
        additional_info = request.form.get('additional_info')
        booking_data['additional_info'] = additional_info
        
        # Traiter les fichiers téléchargés
        if 'documents' not in booking_data:
            booking_data['documents'] = []
        
        files = request.files.getlist('documents')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                file_size = os.path.getsize(file_path)
                
                # Ajouter aux documents en session (sans les données binaires)
                booking_data['documents'].append({
                    'filename': filename,
                    'filetype': file.content_type,
                    'filesize': file_size
                })
                
                # Supprimer le fichier temporaire (il sera sauvegardé après confirmation)
                os.remove(file_path)
        
        # Mettre à jour la session
        session['booking_data'] = booking_data
        
        return render_template('confirmation.html', booking_data=booking_data)
    
    # Si méthode GET, récupérer les données de session
    if 'booking_data' not in session:
        flash('Veuillez commencer par sélectionner un service', 'error')
        return redirect(url_for('index'))
    
    booking_data = session['booking_data']
    
    return render_template('confirmation.html', booking_data=booking_data)


@app.route('/finalize', methods=['POST'])
def finalize():
    """Finaliser les réservations"""
    # Récupérer les données de session
    if 'booking_data' not in session:
        flash('Session expirée. Veuillez recommencer.', 'error')
        return redirect(url_for('index'))
    
    booking_data = session['booking_data']
    
    # Options supplémentaires
    send_confirmation = request.form.get('send_confirmation') == 'on'
    add_to_calendar = request.form.get('add_to_calendar') == 'on'
    
    # Créer les réservations
    bookings_created = []
    for formation in booking_data['formations']:
        new_booking = {
            'service': booking_data['service'],
            'contact': booking_data['contact'],
            'email': booking_data['email'],
            'phone': booking_data.get('phone'),
            'formation_id': formation['formation_id'],
            'formation_name': formation['formation_name'],
            'date': formation['date'],
            'hour': formation['hour'],
            'minutes': formation['minutes'],
            'participants': booking_data['participants'],
            'documents': booking_data.get('documents', []),
            'additional_info': booking_data.get('additional_info'),
            'send_confirmation': send_confirmation
        }
        
        booking_id = db_manager.create_booking(new_booking)
        if booking_id:
            bookings_created.append({
                'id': booking_id,
                'formation_name': formation['formation_name']
            })
    
    # Vider la session
    session.pop('booking_data', None)
    
    if len(bookings_created) == len(booking_data['formations']):
        flash('Toutes les réservations ont été créées avec succès', 'success')
        
        # Si demandé, générer un fichier iCalendar pour l'ajout au calendrier
        if add_to_calendar:
            calendar_file = generate_ical_file(booking_data)
            if calendar_file:
                return send_file(
                    calendar_file,
                    as_attachment=True,
                    download_name='formations-anecoop.ics',
                    mimetype='text/calendar'
                )
        
        return redirect(url_for('thank_you'))
    else:
        flash('Certaines réservations n\'ont pas pu être créées', 'error')
        return redirect(url_for('confirmation'))


@app.route('/thank-you')
def thank_you():
    """Page de remerciement après finalisation"""
    return render_template('thank_you.html')


def generate_ical_file(booking_data):
    """Génère un fichier iCalendar pour les réservations"""
    try:
        from icalendar import Calendar, Event
        from datetime import timedelta
        
        cal = Calendar()
        cal.add('prodid', '-//Anecoop//Formation Booking System//FR')
        cal.add('version', '2.0')
        
        for formation in booking_data['formations']:
            event = Event()
            event.add('summary', formation['formation_name'])
            
            # Créer les dates début/fin
            start_date = datetime.datetime.strptime(formation['date'], '%Y-%m-%d')
            start_date = start_date.replace(hour=formation['hour'], minute=formation['minutes'])
            
            end_date = start_date + timedelta(hours=1, minutes=30)
            
            event.add('dtstart', start_date)
            event.add('dtend', end_date)
            
            # Description
            desc = f"Formation organisée par Anecoop\n"
            desc += f"Responsable: {booking_data['contact']}\n"
            desc += f"Participants: {len(booking_data['participants'])}"
            event.add('description', desc)
            
            event.add('location', 'Anecoop')
            
            cal.add_component(event)
        
        # Enregistrer le fichier
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ics')
        temp_file.write(cal.to_ical())
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Erreur lors de la génération du fichier iCalendar: {e}")
        return None


if __name__ == '__main__':
    # Créer les dossiers nécessaires
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Démarrer l'application
    app.run(debug=True, host='0.0.0.0', port=5000)
