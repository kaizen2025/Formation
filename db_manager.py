# File: db_manager.py
import json
import logging
import datetime
import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool, sql
from psycopg2.errors import UniqueViolation

from config import DATABASE_URL

# Configuration du logging (inchangé)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de connexion et d'opérations pour le schéma normalisé"""

    # __init__, get_connection, release_connection, get_cursor, ping, initialize_database
    # (Inchangés par rapport à la réponse précédente - avec schéma normalisé dans initialize_database)
    # ... (coller le code précédent ici) ...
    def __init__(self):
        """Initialise la connexion à la base de données"""
        max_retries = 5
        retry_delay = 3
        for attempt in range(max_retries):
            try:
                self.connection_pool = pool.ThreadedConnectionPool(
                    minconn=1, maxconn=10, dsn=DATABASE_URL
                )
                logger.info("Pool de connexions DB établi (min=1, max=10)")
                # Ensure tables are created based on normalized schema
                self.initialize_database()
                break
            except psycopg2.OperationalError as e:
                logger.error(f"Erreur connexion DB (Tentative {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.critical("Impossible de se connecter à la DB après plusieurs tentatives.")
                    raise ConnectionError("Connexion DB impossible.") from e
                logger.info(f"Nouvelle tentative dans {retry_delay} sec...")
                time.sleep(retry_delay)
            except Exception as e:
                logger.critical(f"Erreur inattendue init pool connexion: {e}")
                raise

    def get_connection(self):
        """Obtient une connexion depuis le pool"""
        try:
            return self.connection_pool.getconn()
        except Exception as e:
            logger.error(f"Erreur obtention connexion pool: {e}")
            raise ConnectionError("Impossible d'obtenir une connexion DB.") from e

    def release_connection(self, conn):
        """Libère une connexion et la renvoie au pool"""
        if conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Erreur libération connexion pool: {e}")

    @contextmanager
    def get_cursor(self, use_dict_cursor=False, commit_on_exit=False):
        """
        Fournit un curseur DB géré par contexte.
        Acquiert/Libère la connexion. Commit/Rollback optionnel.
        Par défaut, NE COMMIT PAS (laisse le contrôle à l'appelant pour les transactions).
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor_factory = RealDictCursor if use_dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            if commit_on_exit:
                conn.commit()
        except Exception as e:
            logger.error(f"Erreur DB détectée: {e}. Rollback.")
            if conn:
                try:
                    conn.rollback()
                except Exception as rb_err:
                    logger.error(f"Erreur additionnelle durant rollback: {rb_err}")
            raise # Re-raise après rollback
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.release_connection(conn)

    def ping(self):
        """Vérifie la connexion à la base de données"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Erreur ping DB: {e}")
            return False

    def initialize_database(self):
        """Crée les tables du schéma normalisé si elles n'existent pas"""
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                logger.info("Vérification/Création des tables (Schéma Normalisé)...")
                # --- Table Admin User ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS admin_user (
                        id SERIAL PRIMARY KEY, username VARCHAR(64) NOT NULL UNIQUE, password_hash VARCHAR(256) NOT NULL,
                        is_super_admin BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_user_username ON admin_user (username);")
                # --- Table Departments ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS departments ( id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name VARCHAR(100) NOT NULL,
                        description TEXT, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_departments_code ON departments (code);")
                # --- Table Formation Modules ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS formation_modules ( id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name VARCHAR(100) NOT NULL,
                        description TEXT, duration_minutes INTEGER DEFAULT 90, min_participants INTEGER DEFAULT 8, max_participants INTEGER DEFAULT 12,
                        active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fm_code ON formation_modules (code);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fm_active ON formation_modules (active);")
                # --- Table Formation Groups ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS formation_groups ( id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, contact_name VARCHAR(100) NOT NULL,
                        contact_email VARCHAR(100) NOT NULL, contact_phone VARCHAR(20), notes TEXT, department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ, UNIQUE (department_id, name) );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fg_department_id ON formation_groups (department_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fg_contact_email ON formation_groups (contact_email);")
                # --- Table Participants ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS participants ( id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, email VARCHAR(100), position VARCHAR(100),
                        notes TEXT, group_id INTEGER NOT NULL REFERENCES formation_groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_p_group_id ON participants (group_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_p_email ON participants (email);")
                # --- Table Sessions ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions ( id SERIAL PRIMARY KEY, session_date DATE NOT NULL, start_hour INTEGER NOT NULL, start_minutes INTEGER NOT NULL,
                        duration_minutes INTEGER DEFAULT 90, status VARCHAR(20) DEFAULT 'confirmed', additional_info TEXT, location VARCHAR(100) DEFAULT 'Sur site',
                        module_id INTEGER NOT NULL REFERENCES formation_modules(id) ON DELETE CASCADE, group_id INTEGER NOT NULL REFERENCES formation_groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ, UNIQUE (module_id, session_date, start_hour, start_minutes) );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_date ON sessions (session_date);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_status ON sessions (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_module_id ON sessions (module_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_group_id ON sessions (group_id);")
                # --- Table Attendances ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendances ( id SERIAL PRIMARY KEY, present BOOLEAN DEFAULT FALSE, feedback TEXT,
                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                        recorded_by VARCHAR(100), created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ, UNIQUE (session_id, participant_id) );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_session_id ON attendances (session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_participant_id ON attendances (participant_id);")
                # --- Table Documents ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents ( id SERIAL PRIMARY KEY, filename VARCHAR(255) NOT NULL, filetype VARCHAR(100) NOT NULL, filesize INTEGER NOT NULL,
                        filedata BYTEA NOT NULL, description TEXT, is_global BOOLEAN DEFAULT FALSE, uploaded_by_id INTEGER REFERENCES admin_user(id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_is_global ON documents (is_global);")
                # --- Table session_documents (Join) ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_documents ( session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (session_id, document_id) );
                """)
                # --- Table module_documents (Join) ---
                cursor.execute("""
                     CREATE TABLE IF NOT EXISTS module_documents ( module_id INTEGER NOT NULL REFERENCES formation_modules(id) ON DELETE CASCADE, document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                         created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (module_id, document_id) );
                 """)
                # --- Table Waiting List ---
                cursor.execute("""
                     CREATE TABLE IF NOT EXISTS waitlist ( id SERIAL PRIMARY KEY, contact_name VARCHAR(100) NOT NULL, contact_email VARCHAR(100) NOT NULL, contact_phone VARCHAR(20),
                         notes TEXT, status VARCHAR(20) DEFAULT 'waiting', session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                         created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                 """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_session_id ON waitlist (session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_email ON waitlist (contact_email);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_status ON waitlist (status);")
                # --- Table Activity Logs ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs ( id SERIAL PRIMARY KEY, action VARCHAR(50) NOT NULL, user_info JSONB, entity_type VARCHAR(50), entity_id INTEGER,
                        details JSONB, ip_address VARCHAR(45), user_agent TEXT, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP );
                 """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_action ON activity_logs (action);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_entity ON activity_logs (entity_type, entity_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_created_at ON activity_logs (created_at DESC);")
                # --- Table Feedbacks ---
                cursor.execute("""
                     CREATE TABLE IF NOT EXISTS feedbacks ( id SERIAL PRIMARY KEY, type VARCHAR(50) NOT NULL, message TEXT NOT NULL, email VARCHAR(100), contact_name VARCHAR(100),
                         status VARCHAR(20) DEFAULT 'new', response TEXT, session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
                         created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ );
                 """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_status ON feedbacks (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_type ON feedbacks (type);")

                logger.info("Initialisation DB (Schéma Normalisé) terminée.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des tables: {e}", exc_info=True)
            raise

    # --- Departments ---
    def get_all_departments(self) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description FROM departments ORDER BY name")
                return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_all_departments: {e}"); return []
    def get_department_by_id(self, dept_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description FROM departments WHERE id = %s", (dept_id,))
                return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_department_by_id {dept_id}: {e}"); return None
    def create_department(self, data: Dict[str, Any]) -> Optional[int]:
        sql = "INSERT INTO departments (code, name, description) VALUES (%s, %s, %s) RETURNING id"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description')))
                return cursor.fetchone()[0]
        except UniqueViolation: logger.warning(f"Dept code dupliqué: {data.get('code')}"); return -1
        except Exception as e: logger.error(f"Erreur create_department: {e}"); return None
    def update_department(self, dept_id: int, data: Dict[str, Any]) -> bool:
        sql = "UPDATE departments SET code=%s, name=%s, description=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description'), dept_id))
                return cursor.rowcount > 0
        except UniqueViolation: logger.warning(f"Update dept code dupliqué: {data.get('code')}"); return False
        except Exception as e: logger.error(f"Erreur update_department {dept_id}: {e}"); return False
    def delete_department(self, dept_id: int) -> bool:
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute("DELETE FROM departments WHERE id = %s", (dept_id,))
                return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur delete_department {dept_id}: {e}"); return False # Could be Foreign Key Constraint

    # --- Formation Modules ---
    def get_all_modules(self, active_only=True) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                query = "SELECT id, code, name, description, duration_minutes, min_participants, max_participants, active FROM formation_modules"
                if active_only: query += " WHERE active = TRUE"
                query += " ORDER BY name"
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_all_modules: {e}"); return []
    def get_module_by_id(self, module_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description, duration_minutes, min_participants, max_participants, active FROM formation_modules WHERE id = %s", (module_id,))
                return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_module_by_id {module_id}: {e}"); return None
    def create_module(self, data: Dict[str, Any]) -> Optional[int]:
        sql = """INSERT INTO formation_modules (code, name, description, duration_minutes, min_participants, max_participants, active)
                 VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description'), data.get('duration_minutes', 90),
                                    data.get('min_participants', 8), data.get('max_participants', 12), data.get('active', True)))
                return cursor.fetchone()[0]
        except UniqueViolation: logger.warning(f"Module code dupliqué: {data.get('code')}"); return -1
        except Exception as e: logger.error(f"Erreur create_module: {e}"); return None
    def update_module(self, module_id: int, data: Dict[str, Any]) -> bool:
        sql = """UPDATE formation_modules SET code=%s, name=%s, description=%s, duration_minutes=%s, min_participants=%s, max_participants=%s, active=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"""
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description'), data.get('duration_minutes', 90), data.get('min_participants', 8),
                                    data.get('max_participants', 12), data.get('active', True), module_id))
                return cursor.rowcount > 0
        except UniqueViolation: logger.warning(f"Update module code dupliqué: {data.get('code')}"); return False
        except Exception as e: logger.error(f"Erreur update_module {module_id}: {e}"); return False
    def delete_module(self, module_id: int) -> bool:
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute("DELETE FROM formation_modules WHERE id = %s", (module_id,))
                return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur delete_module {module_id}: {e}"); return False # Could be FK Constraint

    # --- Formation Groups ---
    def get_all_groups(self) -> List[Dict[str, Any]]:
        sql = """SELECT g.id, g.name, g.contact_name, g.contact_email, g.contact_phone, g.department_id, d.name as department_name, d.code as department_code
                 FROM formation_groups g LEFT JOIN departments d ON g.department_id = d.id ORDER BY d.name, g.name"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql); return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_all_groups: {e}"); return []
    def get_group_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        sql = """SELECT g.id, g.name, g.contact_name, g.contact_email, g.contact_phone, g.notes, g.department_id, d.name as department_name, d.code as department_code
                 FROM formation_groups g LEFT JOIN departments d ON g.department_id = d.id WHERE g.id = %s"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql, (group_id,)); return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_group_by_id {group_id}: {e}"); return None
    def get_groups_by_contact_email(self, email: str) -> List[Dict[str, Any]]:
        sql = """SELECT g.id, g.name, g.contact_name, g.contact_email, g.contact_phone, g.department_id, d.name as department_name
                 FROM formation_groups g LEFT JOIN departments d ON g.department_id = d.id WHERE LOWER(g.contact_email) = LOWER(%s) ORDER BY d.name, g.name"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql, (email,)); return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_groups_by_contact_email for {email}: {e}"); return []
    def create_group(self, data: Dict[str, Any]) -> Optional[int]:
        sql = """INSERT INTO formation_groups (name, contact_name, contact_email, contact_phone, notes, department_id)
                 VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""
        dept_id = data.get('department_id') if data.get('department_id') != 0 else None # Handle default choice
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['name'], data['contact_name'], data['contact_email'], data.get('contact_phone'), data.get('notes'), dept_id))
                return cursor.fetchone()[0]
        except UniqueViolation: logger.warning(f"Groupe dupliqué: {data.get('name')} pour dept {dept_id}"); return -1
        except Exception as e: logger.error(f"Erreur create_group: {e}"); return None
    def update_group(self, group_id: int, data: Dict[str, Any]) -> bool:
        sql = """UPDATE formation_groups SET name=%s, contact_name=%s, contact_email=%s, contact_phone=%s, notes=%s, department_id=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"""
        dept_id = data.get('department_id') if data.get('department_id') != 0 else None
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['name'], data['contact_name'], data['contact_email'], data.get('contact_phone'), data.get('notes'), dept_id, group_id))
                return cursor.rowcount > 0
        except UniqueViolation: logger.warning(f"Update groupe dupliqué: {data.get('name')} pour dept {dept_id}"); return False
        except Exception as e: logger.error(f"Erreur update_group {group_id}: {e}"); return False
    def delete_group(self, group_id: int) -> bool:
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                # Check dependencies (participants, sessions) first?
                cursor.execute("DELETE FROM formation_groups WHERE id = %s", (group_id,))
                return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur delete_group {group_id}: {e}"); return False

    # --- Participants ---
    def get_participants_by_group(self, group_id: int) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, name, email, position, notes FROM participants WHERE group_id = %s ORDER BY name", (group_id,))
                return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_participants_by_group {group_id}: {e}"); return []
    def get_participant_by_id(self, participant_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, name, email, position, notes, group_id FROM participants WHERE id = %s", (participant_id,))
                return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_participant_by_id {participant_id}: {e}"); return None
    def add_participant_to_group(self, group_id: int, participant_data: Dict[str, Any]) -> Optional[int]:
        sql = "INSERT INTO participants (group_id, name, email, position, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, (group_id, participant_data['name'], participant_data.get('email'), participant_data.get('position'), participant_data.get('notes')))
                 return cursor.fetchone()[0]
        except Exception as e: logger.error(f"Erreur add_participant_to_group for group {group_id}: {e}"); return None
    def update_participant(self, participant_id: int, data: Dict[str, Any]) -> bool:
        sql = "UPDATE participants SET name=%s, email=%s, position=%s, notes=%s, group_id=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['name'], data.get('email'), data.get('position'), data.get('notes'), data['group_id'], participant_id))
                return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur update_participant {participant_id}: {e}"); return False
    def delete_participant(self, participant_id: int) -> bool:
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute("DELETE FROM participants WHERE id = %s", (participant_id,))
                return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur delete_participant {participant_id}: {e}"); return False

    # --- Sessions ---
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        sql = """SELECT s.id, s.session_date, s.start_hour, s.start_minutes, s.status, s.location, m.id as module_id, m.name as module_name, m.code as module_code,
                       g.id as group_id, g.name as group_name, d.id as department_id, d.name as department_name
                 FROM sessions s JOIN formation_modules m ON s.module_id = m.id JOIN formation_groups g ON s.group_id = g.id LEFT JOIN departments d ON g.department_id = d.id
                 ORDER BY s.session_date, s.start_hour, s.start_minutes"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql)
                sessions = cursor.fetchall()
                for s in sessions: s['session_date'] = s['session_date'].isoformat() if isinstance(s.get('session_date'), datetime.date) else s.get('session_date')
                return sessions
        except Exception as e: logger.error(f"Erreur get_all_sessions: {e}"); return []
    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        sql = """SELECT s.*, m.id as module_id, m.name as module_name, m.code as module_code, m.description as module_description,
                       g.id as group_id, g.name as group_name, g.contact_name as group_contact, g.contact_email as group_email, g.contact_phone as group_phone,
                       d.id as department_id, d.name as department_name
                 FROM sessions s JOIN formation_modules m ON s.module_id = m.id JOIN formation_groups g ON s.group_id = g.id LEFT JOIN departments d ON g.department_id = d.id
                 WHERE s.id = %s"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (session_id,))
                session = cursor.fetchone()
                if session:
                    session['session_date'] = session['session_date'].isoformat() if isinstance(session.get('session_date'), datetime.date) else session.get('session_date')
                    session['participants'] = self.get_participants_by_group(session['group_id'])
                    session['documents'] = self.get_documents_metadata_for_session(session_id)
                    session['attendances'] = self.get_attendances_for_session(session_id) # Fetch attendance
                return session
        except Exception as e: logger.error(f"Erreur get_session_by_id {session_id}: {e}"); return None
    def get_sessions_for_group(self, group_id: int) -> List[Dict[str, Any]]:
        sql = """SELECT s.id, s.session_date, s.start_hour, s.start_minutes, s.status, m.name as module_name
                 FROM sessions s JOIN formation_modules m ON s.module_id = m.id
                 WHERE s.group_id = %s ORDER BY s.session_date DESC, s.start_hour"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (group_id,))
                sessions = cursor.fetchall()
                for s in sessions: s['session_date'] = s['session_date'].isoformat() if isinstance(s.get('session_date'), datetime.date) else s.get('session_date')
                return sessions
        except Exception as e: logger.error(f"Erreur get_sessions_for_group {group_id}: {e}"); return []
    def create_session(self, session_data: Dict[str, Any], cursor) -> Optional[int]:
        sql = """INSERT INTO sessions (module_id, group_id, session_date, start_hour, start_minutes, duration_minutes, status, location, additional_info)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        params = (session_data['module_id'], session_data['group_id'], session_data['date'], session_data['hour'], session_data['minutes'],
                  session_data.get('duration_minutes', 90), session_data.get('status', 'confirmed'), session_data.get('location', 'Sur site'), session_data.get('additional_info'))
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]
        except UniqueViolation: logger.warning(f"Session slot conflict: Mod:{session_data.get('module_id')} Date:{session_data.get('date')}"); return -1
        except Exception as e: logger.error(f"Erreur create_session (cursor): {e}"); return None
    def update_session(self, session_id: int, data: Dict[str, Any]) -> bool:
        # Note: Updating date/time/module might cause conflicts, handle carefully
        sql = """UPDATE sessions SET module_id=%s, group_id=%s, session_date=%s, start_hour=%s, start_minutes=%s, duration_minutes=%s,
                 status=%s, location=%s, additional_info=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"""
        params = (data['module_id'], data['group_id'], data['session_date'], data['start_time'].hour, data['start_time'].minute, data.get('duration_minutes', 90),
                  data['status'], data.get('location', 'Sur site'), data.get('additional_info'), session_id)
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, params)
                 return cursor.rowcount > 0
        except UniqueViolation: logger.warning(f"Update session slot conflict: ID:{session_id}"); return False
        except Exception as e: logger.error(f"Erreur update_session {session_id}: {e}"); return False
    def delete_session(self, session_id: int) -> bool:
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
                 return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur delete_session {session_id}: {e}"); return False
    def check_slot_availability(self, module_id: int, date: str, hour: int, minutes: int) -> Dict[str, Any]:
        sql = """SELECT s.id, g.name as group_name FROM sessions s JOIN formation_groups g ON s.group_id = g.id
                 WHERE s.module_id = %s AND s.session_date = %s AND s.start_hour = %s AND s.start_minutes = %s AND s.status != 'canceled'"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (module_id, date, hour, minutes))
                existing_session = cursor.fetchone()
                return {"available": not bool(existing_session), "session": existing_session}
        except Exception as e: logger.error(f"Erreur check_slot_availability: {e}"); return {"available": False, "error": str(e)}

    # --- Attendances ---
    def link_participants_to_session(self, session_id: int, group_id: int, cursor):
        participants = self.get_participants_by_group(group_id)
        if not participants: return True
        sql = "INSERT INTO attendances (session_id, participant_id, present) VALUES (%s, %s, FALSE) ON CONFLICT DO NOTHING"
        try:
            args_list = [(session_id, p['id']) for p in participants]; cursor.executemany(sql, args_list); return True
        except Exception as e: logger.error(f"Erreur link_participants_to_session {session_id} grp {group_id}: {e}"); return False
    def save_attendance(self, data: Dict[str, Any]) -> Optional[int]:
         sql = """INSERT INTO attendances (session_id, participant_id, present, feedback, recorded_by) VALUES (%s, %s, %s, %s, %s)
                  ON CONFLICT (session_id, participant_id) DO UPDATE SET present=EXCLUDED.present, feedback=EXCLUDED.feedback, recorded_by=EXCLUDED.recorded_by, updated_at=CURRENT_TIMESTAMP
                  RETURNING id"""
         try:
             with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, (data['session_id'], data['participant_id'], data.get('present', False), data.get('feedback'), data.get('recorded_by')))
                 return cursor.fetchone()[0]
         except Exception as e: logger.error(f"Erreur save_attendance: {e}"); return None
    def get_attendances_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        sql = """SELECT a.id, a.present, a.feedback, a.participant_id, p.name as participant_name, p.email as participant_email
                 FROM attendances a JOIN participants p ON a.participant_id = p.id WHERE a.session_id = %s ORDER BY p.name"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql, (session_id,)); return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_attendances_for_session {session_id}: {e}"); return []


    # --- Documents ---
    def save_document(self, doc_data: Dict[str, Any], cursor) -> Optional[int]:
        sql = """INSERT INTO documents (filename, filetype, filesize, filedata, description, is_global, uploaded_by_id)
                 VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        params = (doc_data['filename'], doc_data['filetype'], doc_data['filesize'], doc_data['filedata'], doc_data.get('description'),
                  doc_data.get('is_global', False), doc_data.get('uploaded_by_id'))
        try:
            cursor.execute(sql, params); return cursor.fetchone()[0]
        except Exception as e: logger.error(f"Erreur save_document '{doc_data.get('filename')}': {e}"); return None
    def associate_document_to_session(self, document_id: int, session_id: int, cursor) -> bool:
        sql = "INSERT INTO session_documents (session_id, document_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        try:
            cursor.execute(sql, (session_id, document_id)); return True
        except Exception as e: logger.error(f"Erreur associate_document_to_session doc:{document_id} sess:{session_id}: {e}"); return False
    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute("SELECT id, filename, filetype, filesize, filedata, description, is_global, uploaded_by_id, created_at FROM documents WHERE id = %s", (document_id,))
                 return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_document_by_id {document_id}: {e}"); return None
    def get_documents_metadata(self) -> List[Dict[str, Any]]:
        sql = "SELECT id, filename, filetype, filesize, description, is_global FROM documents ORDER BY filename"
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql); return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_documents_metadata: {e}"); return []
    def get_documents_metadata_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        sql = """SELECT d.id, d.filename, d.filetype, d.filesize, d.description, d.is_global FROM documents d
                 JOIN session_documents sd ON d.id = sd.document_id WHERE sd.session_id = %s ORDER BY d.filename"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor: cursor.execute(sql, (session_id,)); return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_documents_metadata_for_session {session_id}: {e}"); return []
    def get_global_documents(self) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute("SELECT id, filename, filetype, filesize, description FROM documents WHERE is_global = TRUE ORDER BY filename")
                 return cursor.fetchall()
        except Exception as e: logger.error(f"Erreur get_global_documents: {e}"); return []
    def delete_document(self, document_id: int) -> bool:
         try:
             with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
                 return cursor.rowcount > 0
         except Exception as e: logger.error(f"Erreur delete_document {document_id}: {e}"); return False

    # --- Waitlist ---
    def add_to_waitlist(self, waitlist_data: Dict[str, Any]) -> Optional[int]:
        sql = """INSERT INTO waitlist (session_id, contact_name, contact_email, contact_phone, notes, status)
                 VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""
        params = (waitlist_data['session_id'], waitlist_data['contact_name'], waitlist_data['contact_email'],
                  waitlist_data.get('contact_phone'), waitlist_data.get('notes'), waitlist_data.get('status', 'waiting'))
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, params); return cursor.fetchone()[0]
        except Exception as e: logger.error(f"Erreur add_to_waitlist: {e}"); return None
    def get_waiting_list(self) -> List[Dict[str, Any]]:
        sql = """SELECT w.*, s.session_date, m.name as module_name FROM waitlist w
                 JOIN sessions s ON w.session_id = s.id JOIN formation_modules m ON s.module_id = m.id
                 ORDER BY w.created_at"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute(sql)
                 wl = cursor.fetchall()
                 for item in wl: item['session_date'] = item['session_date'].isoformat() if isinstance(item.get('session_date'), datetime.date) else item.get('session_date')
                 return wl
        except Exception as e: logger.error(f"Erreur get_waiting_list: {e}"); return []
    def get_waitlist_by_email(self, email: str) -> List[Dict[str, Any]]:
        sql = """SELECT w.*, s.session_date, m.name as module_name FROM waitlist w
                 JOIN sessions s ON w.session_id = s.id JOIN formation_modules m ON s.module_id = m.id
                 WHERE LOWER(w.contact_email) = LOWER(%s) ORDER BY w.created_at"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute(sql, (email,))
                 wl = cursor.fetchall()
                 for item in wl: item['session_date'] = item['session_date'].isoformat() if isinstance(item.get('session_date'), datetime.date) else item.get('session_date')
                 return wl
        except Exception as e: logger.error(f"Erreur get_waitlist_by_email for {email}: {e}"); return []
    def remove_from_waitlist(self, waitlist_id: int) -> bool:
         try:
             with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute("DELETE FROM waitlist WHERE id = %s", (waitlist_id,)); return cursor.rowcount > 0
         except Exception as e: logger.error(f"Erreur remove_from_waitlist {waitlist_id}: {e}"); return False
    def update_waitlist_status(self, waitlist_id: int, status: str) -> bool:
         try:
             with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute("UPDATE waitlist SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s", (status, waitlist_id)); return cursor.rowcount > 0
         except Exception as e: logger.error(f"Erreur update_waitlist_status {waitlist_id}: {e}"); return False

    # --- Activity Logs ---
    def add_activity_log(self, action: str, user_info: Optional[Dict]=None, details: Optional[Dict]=None, entity_type: Optional[str]=None, entity_id: Optional[int]=None, ip_address: Optional[str]=None, user_agent: Optional[str]=None):
        sql = "INSERT INTO activity_logs (action, user_info, details, entity_type, entity_id, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        params = (action, json.dumps(user_info) if user_info else None, json.dumps(details) if details else None, entity_type, entity_id, ip_address, user_agent)
        try:
            with self.get_cursor(commit_on_exit=True) as cursor: cursor.execute(sql, params)
        except Exception as e: logger.error(f"Erreur add_activity_log ({action}): {e}")
    def get_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        sql = "SELECT id, action, user_info, details, entity_type, entity_id, ip_address, user_agent, created_at FROM activity_logs ORDER BY created_at DESC LIMIT %s"
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (limit,))
                logs = cursor.fetchall()
                for log in logs: log['created_at'] = log['created_at'].isoformat() if isinstance(log.get('created_at'), datetime.datetime) else log.get('created_at')
                return logs
        except Exception as e: logger.error(f"Erreur get_activity_logs: {e}"); return []

    # --- Feedback ---
    def save_feedback(self, feedback_data: Dict[str, Any]) -> Optional[int]:
        sql = """INSERT INTO feedbacks (type, message, email, contact_name, status, session_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""
        params = (feedback_data.get('type', 'comment'), feedback_data['message'], feedback_data.get('email'), feedback_data.get('contact_name'), feedback_data.get('status', 'new'), feedback_data.get('session_id'))
        try:
            with self.get_cursor(commit_on_exit=True) as cursor: cursor.execute(sql, params); return cursor.fetchone()[0]
        except Exception as e: logger.error(f"Erreur save_feedback: {e}"); return None
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        sql = "SELECT f.*, s.session_date, m.name as module_name FROM feedbacks f LEFT JOIN sessions s ON f.session_id = s.id LEFT JOIN formation_modules m ON s.module_id = m.id ORDER BY f.created_at DESC"
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql)
                fb = cursor.fetchall()
                for item in fb:
                    item['created_at'] = item['created_at'].isoformat() if isinstance(item.get('created_at'), datetime.datetime) else item.get('created_at')
                    item['session_date'] = item['session_date'].isoformat() if isinstance(item.get('session_date'), datetime.date) else item.get('session_date')
                return fb
        except Exception as e: logger.error(f"Erreur get_all_feedback: {e}"); return []
    def get_feedback_by_status(self, status: str) -> List[Dict[str, Any]]:
        # Similaire à get_all_feedback mais avec WHERE f.status = %s
        sql = "SELECT f.*, s.session_date, m.name as module_name FROM feedbacks f LEFT JOIN sessions s ON f.session_id = s.id LEFT JOIN formation_modules m ON s.module_id = m.id WHERE f.status = %s ORDER BY f.created_at DESC"
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (status,))
                fb = cursor.fetchall()
                # Format dates...
                return fb
        except Exception as e: logger.error(f"Erreur get_feedback_by_status '{status}': {e}"); return []
    def update_feedback_status(self, feedback_id: int, status: str, response: Optional[str] = None) -> bool:
        sql = "UPDATE feedbacks SET status=%s, response=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (status, response, feedback_id)); return cursor.rowcount > 0
        except Exception as e: logger.error(f"Erreur update_feedback_status {feedback_id}: {e}"); return False

    # --- Admin User ---
    def get_admin_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, username, password_hash, is_super_admin FROM admin_user WHERE username = %s", (username,)); return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_admin_user_by_username {username}: {e}"); return None
    def get_admin_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, username, password_hash, is_super_admin FROM admin_user WHERE id = %s", (user_id,)); return cursor.fetchone()
        except Exception as e: logger.error(f"Erreur get_admin_user_by_id {user_id}: {e}"); return None

    # --- Stats (Adapté) ---
    def get_dashboard_stats(self) -> Dict[str, Any]:
        stats = {'total_sessions': 0, 'total_participants': 0, 'sessions_by_department': {}, 'waiting_list_count': 0, 'new_feedback_count': 0}
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM sessions WHERE status != 'canceled'"); stats['total_sessions'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(DISTINCT p.id) as total FROM participants p JOIN formation_groups g ON p.group_id = g.id JOIN sessions s ON s.group_id = g.id WHERE s.status != 'canceled'"); stats['total_participants'] = cursor.fetchone()['total']
                cursor.execute("""SELECT d.name, COUNT(s.id) as count FROM sessions s JOIN formation_groups g ON s.group_id = g.id JOIN departments d ON g.department_id = d.id
                                  WHERE s.status != 'canceled' GROUP BY d.name"""); stats['sessions_by_department'] = {row['name']: row['count'] for row in cursor.fetchall()}
                cursor.execute("SELECT COUNT(*) as total FROM waitlist WHERE status = 'waiting'"); stats['waiting_list_count'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM feedbacks WHERE status = 'new'"); stats['new_feedback_count'] = cursor.fetchone()['total']
            return stats
        except Exception as e: logger.error(f"Erreur get_dashboard_stats: {e}"); return stats

    # --- close_pool (inchangé) ---
    def close_pool(self):
        if hasattr(self, 'connection_pool') and self.connection_pool:
            try: self.connection_pool.closeall(); logger.info("Pool DB fermé.")
            except Exception as e: logger.error(f"Erreur fermeture pool: {e}")

# --- Instance Creation (inchangé) ---
db_manager = None
try: db_manager = DatabaseManager()
except ConnectionError as e: logger.critical(f"CRITICAL: Echec init DatabaseManager - {e}"); db_manager = None
except Exception as e: logger.critical(f"CRITICAL: Erreur inattendue init DatabaseManager - {e}"); db_manager = None
