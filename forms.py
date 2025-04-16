# File: forms.py
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, BooleanField,
                     SelectField, TextAreaField, IntegerField, DateField,
                     TimeField, HiddenField, MultipleFileField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, ValidationError
from flask_wtf.file import FileAllowed
# Importer db_manager pour peupler les choix dynamiquement au moment de l'instanciation
# C'est moins idéal que d'utiliser des requêtes ORM, mais faisable.
from db_manager import db_manager
from config import MIN_PARTICIPANTS, MAX_PARTICIPANTS, ALLOWED_EXTENSIONS

# --- Formulaires Admin ---

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Connexion')

class DepartmentForm(FlaskForm):
    code = StringField('Code unique', validators=[DataRequired(), Length(max=50)])
    name = StringField('Nom du département', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Enregistrer')

class ModuleForm(FlaskForm):
    code = StringField('Code unique', validators=[DataRequired(), Length(max=50)])
    name = StringField('Nom du module', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    duration_minutes = IntegerField('Durée (minutes)', default=90, validators=[DataRequired(), NumberRange(min=15)])
    min_participants = IntegerField('Min Participants', default=MIN_PARTICIPANTS, validators=[DataRequired(), NumberRange(min=1)])
    max_participants = IntegerField('Max Participants', default=MAX_PARTICIPANTS, validators=[DataRequired(), NumberRange(min=1)])
    active = BooleanField('Actif', default=True)
    submit = SubmitField('Enregistrer')

class GroupForm(FlaskForm):
    name = StringField('Nom du groupe', validators=[DataRequired(), Length(max=100)])
    contact_name = StringField('Nom du contact', validators=[DataRequired(), Length(max=100)])
    contact_email = StringField('Email du contact', validators=[DataRequired(), Email(), Length(max=100)])
    contact_phone = StringField('Téléphone du contact', validators=[Optional(), Length(max=20)])
    department_id = SelectField('Département', coerce=int, validators=[DataRequired(message="Sélectionnez un département")])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Enregistrer')

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        # Peupler les choix de département
        if db_manager:
            departments = db_manager.get_all_departments()
            self.department_id.choices = [(d['id'], d['name']) for d in departments]
        else:
            self.department_id.choices = []
        self.department_id.choices.insert(0, (0, '--- Sélectionner ---')) # Ajout choix par défaut

class SessionForm(FlaskForm):
    module_id = SelectField('Module de formation', coerce=int, validators=[DataRequired(message="Sélectionnez un module")])
    group_id = SelectField('Groupe de formation', coerce=int, validators=[DataRequired(message="Sélectionnez un groupe")])
    session_date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    start_time = TimeField('Heure de début', validators=[DataRequired()], format='%H:%M')
    duration_minutes = IntegerField('Durée (minutes)', validators=[Optional(), NumberRange(min=15)]) # Durée du module est prioritaire
    location = StringField('Lieu', default='Sur site', validators=[Optional(), Length(max=100)])
    status = SelectField('Statut', choices=[('confirmed', 'Confirmé'), ('canceled', 'Annulé'), ('completed', 'Terminé')], default='confirmed', validators=[DataRequired()])
    additional_info = TextAreaField('Informations supplémentaires', validators=[Optional()])
    submit = SubmitField('Enregistrer la session')

    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)
        # Peupler les choix dynamiquement
        if db_manager:
            modules = db_manager.get_all_modules(active_only=True)
            groups = db_manager.get_all_groups()
            self.module_id.choices = [(m['id'], m['name']) for m in modules]
            self.group_id.choices = [(g['id'], f"{g['name']} ({g['department_name']})") for g in groups]
        else:
            self.module_id.choices = []
            self.group_id.choices = []
        self.module_id.choices.insert(0, (0, '--- Sélectionner Module ---'))
        self.group_id.choices.insert(0, (0, '--- Sélectionner Groupe ---'))


class ParticipantForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=100)])
    position = StringField('Poste', validators=[Optional(), Length(max=100)])
    group_id = SelectField('Groupe', coerce=int, validators=[DataRequired(message="Sélectionnez un groupe")])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Enregistrer Participant')

    def __init__(self, *args, **kwargs):
        super(ParticipantForm, self).__init__(*args, **kwargs)
        if db_manager:
            groups = db_manager.get_all_groups()
            self.group_id.choices = [(g['id'], f"{g['name']} ({g['department_name']})") for g in groups]
        else:
             self.group_id.choices = []
        self.group_id.choices.insert(0, (0, '--- Sélectionner Groupe ---'))

class DocumentUploadForm(FlaskForm):
    file = MultipleFileField('Fichiers', validators=[DataRequired(), FileAllowed(ALLOWED_EXTENSIONS, 'Type de fichier non autorisé!')])
    description = TextAreaField('Description', validators=[Optional()])
    is_global = BooleanField('Document global (accessible à tous)', default=False)
    submit = SubmitField('Télécharger')

class FeedbackResponseForm(FlaskForm):
    response = TextAreaField('Réponse', validators=[DataRequired()])
    status = SelectField('Nouveau statut', choices=[('new', 'Nouveau'), ('read', 'Lu'), ('addressed', 'Traité'), ('archived', 'Archivé')], validators=[DataRequired()])
    submit = SubmitField('Enregistrer la réponse')

# --- Formulaires Flux Réservation ---

class SelectGroupForm(FlaskForm):
    group_id = SelectField('Votre département/groupe', coerce=int, validators=[DataRequired(message="Veuillez sélectionner votre groupe.")])
    submit = SubmitField('Choisir les formations <i class="fas fa-arrow-right ms-2"></i>')

    def __init__(self, *args, **kwargs):
        super(SelectGroupForm, self).__init__(*args, **kwargs)
        if db_manager:
            groups = db_manager.get_all_groups()
            self.group_id.choices = [(g['id'], f"{g['name']} ({g['department_name']})") for g in groups]
        else:
            self.group_id.choices = []
        self.group_id.choices.insert(0, (0, "--- Sélectionnez votre groupe ---"))

class SelectModulesForm(FlaskForm):
    selected_slots = HiddenField('selected_slots', validators=[DataRequired(message="Veuillez sélectionner au moins un créneau.")])
    submit = SubmitField('Ajouter les participants <i class="fas fa-arrow-right ms-2"></i>')

    def validate_selected_slots(self, field):
        import json
        try:
            slots = json.loads(field.data)
            if not isinstance(slots, list) or not slots:
                raise ValidationError('Veuillez sélectionner au moins un créneau de formation.')
            for slot in slots:
                if not all(k in slot for k in ('module_id', 'date', 'hour', 'minutes')):
                    raise ValidationError('Données de créneau invalides.')
                # Vérifier types
                int(slot['module_id']); int(slot['hour']); int(slot['minutes'])
                datetime.date.fromisoformat(slot['date'])
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            raise ValidationError('Format de sélection de créneau invalide.')

class ParticipantsBookingForm(FlaskForm):
    participants_json = HiddenField('participants_json', validators=[DataRequired()])
    # Passer min/max via render_template, validation dans la route ou ici
    submit = SubmitField('Gérer les documents <i class="fas fa-arrow-right ms-2"></i>')

    def validate_participants_json(self, field):
        import json
        try:
            participants = json.loads(field.data or '[]')
            if not isinstance(participants, list):
                raise ValidationError("Format des participants invalide.")
            # La validation du nombre est faite dans la route avec MIN/MAX_PARTICIPANTS
            if not (MIN_PARTICIPANTS <= len(participants) <= MAX_PARTICIPANTS):
                 raise ValidationError(f"Le nombre de participants ({len(participants)}) doit être compris entre {MIN_PARTICIPANTS} et {MAX_PARTICIPANTS}.")
            for p in participants:
                if not p.get('name', '').strip():
                    raise ValidationError("Le nom de chaque participant est requis.")
                # Email format validation using WTForms Email validator
                if p.get('email'):
                    email_validator = Email(message=f"L'email '{p['email']}' est invalide.")
                    try:
                        # Need a dummy field to call the validator
                        dummy_field = StringField()
                        dummy_field.data = p['email']
                        email_validator(self, dummy_field) # Raises ValidationError on failure
                    except ValidationError as e:
                         raise ValidationError(str(e)) # Re-raise with the message
        except (json.JSONDecodeError, TypeError) as e:
            raise ValidationError(f"Erreur lors de la validation des participants: {e}")


class DocumentsBookingForm(FlaskForm):
    uploaded_documents = MultipleFileField('Télécharger des documents spécifiques (Optionnel)', validators=[
        Optional(), FileAllowed(ALLOWED_EXTENSIONS, 'Type de fichier non autorisé.')
    ])
    global_documents = SelectMultipleField('Sélectionner des documents de la bibliothèque (Optionnel)', coerce=int, validators=[Optional()])
    additional_info = TextAreaField('Informations supplémentaires ou commentaires (Optionnel)', validators=[Optional()])
    submit = SubmitField('Vérifier la réservation <i class="fas fa-arrow-right ms-2"></i>')

    def __init__(self, *args, **kwargs):
        super(DocumentsBookingForm, self).__init__(*args, **kwargs)
        if db_manager:
            global_docs = db_manager.get_global_documents()
            self.global_documents.choices = [(d['id'], d['filename']) for d in global_docs]
        else:
            self.global_documents.choices = []

class FinalConfirmationForm(FlaskForm):
    send_confirmation = BooleanField('Envoyer un email de confirmation au contact et aux participants', default=True)
    submit = SubmitField('Confirmer et Finaliser la Réservation <i class="fas fa-check ms-2"></i>')

# --- Formulaires Utilisateur ---

class UserDashboardLinkForm(FlaskForm):
    email = StringField('Votre adresse email de contact', validators=[DataRequired(), Email()])
    submit = SubmitField('Recevoir le lien du tableau de bord')

class FeedbackForm(FlaskForm):
    type = SelectField('Type de feedback', choices=[('bug', 'Signaler un Bug'), ('suggestion', 'Suggestion'), ('comment', 'Commentaire Général')], validators=[DataRequired()])
    message = TextAreaField('Votre message', validators=[DataRequired(), Length(min=10)])
    email = StringField('Votre Email (optionnel)', validators=[Optional(), Email()])
    contact_name = StringField('Votre Nom (optionnel)', validators=[Optional()])
    submit = SubmitField('Envoyer le Feedback')
