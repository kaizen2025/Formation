# File: db_manager.py
import json
import logging
import datetime
import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool, sql # Importer sql pour les requêtes dynamiques sécurisées
from psycopg2.errors import UniqueViolation # Importer pour gérer les conflits

from config import DATABASE_URL # Importer depuis le config modifié

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de connexion et d'opérations pour le schéma normalisé"""

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
                self.initialize_database() # Crée les tables si elles n'existent pas
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
            # Utilise commit_on_exit=False (par défaut) car SELECT ne modifie rien
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Erreur ping DB: {e}")
            return False

    def initialize_database(self):
        """Crée les tables du schéma normalisé si elles n'existent pas"""
        # ATTENTION: Ceci est une initialisation simple. Pour des migrations complexes
        # ou des mises à jour de schéma, un outil comme Alembic est recommandé.
        try:
            # Utilise commit_on_exit=True car CREATE TABLE modifie le schéma
            with self.get_cursor(commit_on_exit=True) as cursor:
                logger.info("Vérification/Création des tables (Schéma Normalisé)...")

                # --- Table Admin User ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS admin_user (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(64) NOT NULL UNIQUE,
                        password_hash VARCHAR(256) NOT NULL,
                        is_super_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_user_username ON admin_user (username);")


                # --- Table Departments ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS departments (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(50) NOT NULL UNIQUE,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_departments_code ON departments (code);")

                # --- Table Formation Modules ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS formation_modules (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(50) NOT NULL UNIQUE,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        duration_minutes INTEGER DEFAULT 90,
                        min_participants INTEGER DEFAULT 8,
                        max_participants INTEGER DEFAULT 12,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fm_code ON formation_modules (code);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fm_active ON formation_modules (active);")


                # --- Table Formation Groups ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS formation_groups (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        contact_name VARCHAR(100) NOT NULL,
                        contact_email VARCHAR(100) NOT NULL,
                        contact_phone VARCHAR(20),
                        notes TEXT,
                        department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ,
                        UNIQUE (department_id, name)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fg_department_id ON formation_groups (department_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fg_contact_email ON formation_groups (contact_email);")

                # --- Table Participants ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS participants (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100),
                        position VARCHAR(100),
                        notes TEXT,
                        group_id INTEGER NOT NULL REFERENCES formation_groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_p_group_id ON participants (group_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_p_email ON participants (email);")


                # --- Table Sessions ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        session_date DATE NOT NULL,
                        start_hour INTEGER NOT NULL,
                        start_minutes INTEGER NOT NULL,
                        duration_minutes INTEGER DEFAULT 90,
                        status VARCHAR(20) DEFAULT 'confirmed', -- confirmed, canceled, completed
                        additional_info TEXT,
                        location VARCHAR(100) DEFAULT 'Sur site',
                        module_id INTEGER NOT NULL REFERENCES formation_modules(id) ON DELETE CASCADE,
                        group_id INTEGER NOT NULL REFERENCES formation_groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ,
                        UNIQUE (module_id, session_date, start_hour, start_minutes)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_date ON sessions (session_date);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_status ON sessions (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_module_id ON sessions (module_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_s_group_id ON sessions (group_id);")


                # --- Table Attendances ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendances (
                        id SERIAL PRIMARY KEY,
                        present BOOLEAN DEFAULT FALSE,
                        feedback TEXT,
                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                        participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                        recorded_by VARCHAR(100),
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ,
                        UNIQUE (session_id, participant_id)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_session_id ON attendances (session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_participant_id ON attendances (participant_id);")

                # --- Table Documents ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        filetype VARCHAR(100) NOT NULL,
                        filesize INTEGER NOT NULL,
                        filedata BYTEA NOT NULL,
                        description TEXT,
                        is_global BOOLEAN DEFAULT FALSE,
                        uploaded_by_id INTEGER REFERENCES admin_user(id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_is_global ON documents (is_global);")

                # --- Table session_documents (Join) ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_documents (
                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (session_id, document_id)
                    );
                """)

                # --- Table module_documents (Join) ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS module_documents (
                        module_id INTEGER NOT NULL REFERENCES formation_modules(id) ON DELETE CASCADE,
                        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (module_id, document_id)
                    );
                 """)

                # --- Table Waiting List ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS waitlist (
                        id SERIAL PRIMARY KEY,
                        contact_name VARCHAR(100) NOT NULL,
                        contact_email VARCHAR(100) NOT NULL,
                        contact_phone VARCHAR(20),
                        notes TEXT,
                        status VARCHAR(20) DEFAULT 'waiting', -- waiting, contacted, promoted, canceled
                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_session_id ON waitlist (session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_email ON waitlist (contact_email);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_status ON waitlist (status);")

                # --- Table Activity Logs ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id SERIAL PRIMARY KEY,
                        action VARCHAR(50) NOT NULL,
                        user_info JSONB, -- {'admin_id': 1, 'username': 'admin'} or {'user_email': '...', 'group_id': 5}
                        entity_type VARCHAR(50), -- 'Session', 'Document', 'Participant', etc.
                        entity_id INTEGER,
                        details JSONB, -- Specific details of the action
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_action ON activity_logs (action);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_entity ON activity_logs (entity_type, entity_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_created_at ON activity_logs (created_at DESC);")

                # --- Table Feedbacks ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedbacks (
                        id SERIAL PRIMARY KEY,
                        type VARCHAR(50) NOT NULL, -- bug, suggestion, comment
                        message TEXT NOT NULL,
                        email VARCHAR(100),
                        contact_name VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'new', -- new, read, addressed, archived
                        response TEXT, -- Admin response
                        session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_status ON feedbacks (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_type ON feedbacks (type);")

                logger.info("Initialisation DB (Schéma Normalisé) terminée.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des tables: {e}", exc_info=True)
            raise # Re-raise pour indiquer l'échec

    # --- Méthodes CRUD adaptées ---
    # (Implémentation partielle - à compléter)

    # --- Departments ---
    def get_all_departments(self) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description FROM departments ORDER BY name")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur get_all_departments: {e}")
            return []

    def get_department_by_id(self, dept_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description FROM departments WHERE id = %s", (dept_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur get_department_by_id {dept_id}: {e}")
            return None

    def create_department(self, data: Dict[str, Any]) -> Optional[int]:
        sql = "INSERT INTO departments (code, name, description) VALUES (%s, %s, %s) RETURNING id"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor: # Commit here
                cursor.execute(sql, (data['code'], data['name'], data.get('description')))
                dept_id = cursor.fetchone()[0]
                # Consider adding activity log here
                return dept_id
        except UniqueViolation:
             logger.warning(f"Tentative de création de département avec code dupliqué: {data.get('code')}")
             return -1 # Indicate duplicate error
        except Exception as e:
            logger.error(f"Erreur create_department: {e}")
            return None

    def update_department(self, dept_id: int, data: Dict[str, Any]) -> bool:
         sql = """
             UPDATE departments SET code = %s, name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
         """
         try:
             with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, (data['code'], data['name'], data.get('description'), dept_id))
                 return cursor.rowcount > 0
         except UniqueViolation:
             logger.warning(f"Tentative de mise à jour de département avec code dupliqué: {data.get('code')}")
             return False
         except Exception as e:
             logger.error(f"Erreur update_department {dept_id}: {e}")
             return False

    def delete_department(self, dept_id: int) -> bool:
        # Attention: vérifier les dépendances (groups) avant suppression ou utiliser ON DELETE SET NULL/CASCADE
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                # Peut-être vérifier si des groupes existent pour ce département d'abord ?
                cursor.execute("DELETE FROM departments WHERE id = %s", (dept_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erreur delete_department {dept_id}: {e}")
            return False


    # --- Formation Modules ---
    def get_all_modules(self, active_only=True) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                query = "SELECT id, code, name, description, duration_minutes, min_participants, max_participants, active FROM formation_modules"
                params = []
                if active_only:
                    query += " WHERE active = TRUE"
                query += " ORDER BY name"
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur get_all_modules: {e}")
            return []

    def get_module_by_id(self, module_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, code, name, description, duration_minutes, min_participants, max_participants, active FROM formation_modules WHERE id = %s", (module_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur get_module_by_id {module_id}: {e}")
            return None

    def create_module(self, data: Dict[str, Any]) -> Optional[int]:
        sql = """INSERT INTO formation_modules
                 (code, name, description, duration_minutes, min_participants, max_participants, active)
                 VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description'),
                                    data.get('duration_minutes', 90), data.get('min_participants', 8),
                                    data.get('max_participants', 12), data.get('active', True)))
                module_id = cursor.fetchone()[0]
                return module_id
        except UniqueViolation:
             logger.warning(f"Tentative de création de module avec code dupliqué: {data.get('code')}")
             return -1
        except Exception as e:
            logger.error(f"Erreur create_module: {e}")
            return None

    def update_module(self, module_id: int, data: Dict[str, Any]) -> bool:
        sql = """UPDATE formation_modules SET
                 code=%s, name=%s, description=%s, duration_minutes=%s, min_participants=%s,
                 max_participants=%s, active=%s, updated_at=CURRENT_TIMESTAMP
                 WHERE id = %s"""
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, (data['code'], data['name'], data.get('description'),
                                    data.get('duration_minutes', 90), data.get('min_participants', 8),
                                    data.get('max_participants', 12), data.get('active', True), module_id))
                return cursor.rowcount > 0
        except UniqueViolation:
             logger.warning(f"Tentative de mise à jour de module avec code dupliqué: {data.get('code')}")
             return False
        except Exception as e:
            logger.error(f"Erreur update_module {module_id}: {e}")
            return False

    def delete_module(self, module_id: int) -> bool:
        # Vérifier dépendances (sessions) avant suppression ?
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute("DELETE FROM formation_modules WHERE id = %s", (module_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erreur delete_module {module_id}: {e}")
            return False

    # --- Formation Groups ---
    def get_all_groups(self) -> List[Dict[str, Any]]:
        sql = """SELECT g.id, g.name, g.contact_name, g.contact_email, g.contact_phone,
                       g.department_id, d.name as department_name, d.code as department_code
                 FROM formation_groups g
                 LEFT JOIN departments d ON g.department_id = d.id
                 ORDER BY d.name, g.name"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur get_all_groups: {e}")
            return []

    def get_group_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        sql = """SELECT g.id, g.name, g.contact_name, g.contact_email, g.contact_phone, g.notes,
                       g.department_id, d.name as department_name, d.code as department_code
                 FROM formation_groups g
                 LEFT JOIN departments d ON g.department_id = d.id
                 WHERE g.id = %s"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (group_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur get_group_by_id {group_id}: {e}")
            return None

    # ... CRUD pour Groups ...

    # --- Participants ---
    def get_participants_by_group(self, group_id: int) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, name, email, position FROM participants WHERE group_id = %s ORDER BY name", (group_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur get_participants_by_group {group_id}: {e}")
            return []

    def add_participant_to_group(self, group_id: int, participant_data: Dict[str, Any]) -> Optional[int]:
        sql = "INSERT INTO participants (group_id, name, email, position, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id"
        try:
            with self.get_cursor(commit_on_exit=True) as cursor:
                 cursor.execute(sql, (group_id, participant_data['name'], participant_data.get('email'),
                                     participant_data.get('position'), participant_data.get('notes')))
                 return cursor.fetchone()[0]
        except Exception as e:
             logger.error(f"Erreur add_participant_to_group for group {group_id}: {e}")
             return None

    # ... CRUD pour Participants ...


    # --- Sessions ---
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                s.id, s.session_date, s.start_hour, s.start_minutes, s.status,
                s.location, s.additional_info,
                m.id as module_id, m.name as module_name, m.code as module_code,
                g.id as group_id, g.name as group_name, g.contact_name as group_contact,
                d.id as department_id, d.name as department_name
            FROM sessions s
            JOIN formation_modules m ON s.module_id = m.id
            JOIN formation_groups g ON s.group_id = g.id
            LEFT JOIN departments d ON g.department_id = d.id
            ORDER BY s.session_date, s.start_hour, s.start_minutes
        """
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql)
                # Convert date to string for JSON compatibility if needed by frontend
                sessions = cursor.fetchall()
                for session in sessions:
                    if isinstance(session['session_date'], datetime.date):
                         session['session_date'] = session['session_date'].isoformat()
                return sessions
        except Exception as e:
            logger.error(f"Erreur get_all_sessions: {e}")
            return []

    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT
                s.id, s.session_date, s.start_hour, s.start_minutes, s.duration_minutes, s.status,
                s.location, s.additional_info, s.created_at, s.updated_at,
                m.id as module_id, m.name as module_name, m.code as module_code, m.description as module_description,
                g.id as group_id, g.name as group_name, g.contact_name as group_contact, g.contact_email as group_email, g.contact_phone as group_phone,
                d.id as department_id, d.name as department_name
            FROM sessions s
            JOIN formation_modules m ON s.module_id = m.id
            JOIN formation_groups g ON s.group_id = g.id
            LEFT JOIN departments d ON g.department_id = d.id
            WHERE s.id = %s
        """
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (session_id,))
                session = cursor.fetchone()
                if session:
                    if isinstance(session['session_date'], datetime.date):
                         session['session_date'] = session['session_date'].isoformat()
                    # Fetch participants for this session's group
                    session['participants'] = self.get_participants_by_group(session['group_id'])
                    # Fetch documents for this session
                    session['documents'] = self.get_documents_metadata_for_session(session_id)
                return session
        except Exception as e:
            logger.error(f"Erreur get_session_by_id {session_id}: {e}")
            return None

    def create_session(self, session_data: Dict[str, Any]) -> Optional[int]:
        """ Crée une session. La gestion des participants/attendances se fait après."""
        sql = """
            INSERT INTO sessions (module_id, group_id, session_date, start_hour, start_minutes,
                                  duration_minutes, status, location, additional_info)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            session_data['module_id'],
            session_data['group_id'],
            session_data['date'],
            session_data['hour'],
            session_data['minutes'],
            session_data.get('duration_minutes', 90),
            session_data.get('status', 'confirmed'),
            session_data.get('location', 'Sur site'),
            session_data.get('additional_info')
        )
        try:
            # Important: Ne pas commiter ici si fait partie d'une transaction plus large (finalize)
            # Utiliser le curseur retourné par get_cursor sans commit_on_exit=True
            # L'appelant (ex: finalize) devra gérer le commit/rollback
            # Si c'est une création simple (admin), on peut commiter ici
            with self.get_cursor(commit_on_exit=True) as cursor: # Commit for simple creation
                cursor.execute(sql, params)
                session_id = cursor.fetchone()[0]
                return session_id
        except UniqueViolation:
             logger.warning(f"Tentative de création de session sur un créneau déjà pris: Module {session_data.get('module_id')} le {session_data.get('date')} à {session_data.get('hour')}:{session_data.get('minutes')}")
             return -1 # Indicate conflict
        except Exception as e:
            logger.error(f"Erreur create_session: {e}")
            # Ne pas commiter si erreur
            return None

    # ... Update/Delete pour Sessions ...

    def check_slot_availability(self, module_id: int, date: str, hour: int, minutes: int) -> Dict[str, Any]:
        """ Vérifie si un créneau est déjà pris pour un module spécifique """
        sql = """
            SELECT s.id, g.name as group_name
            FROM sessions s
            JOIN formation_groups g ON s.group_id = g.id
            WHERE s.module_id = %s AND s.session_date = %s AND s.start_hour = %s AND s.start_minutes = %s
              AND s.status != 'canceled'
        """
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (module_id, date, hour, minutes))
                existing_session = cursor.fetchone()
                if existing_session:
                    return {"available": False, "session": existing_session}
                else:
                    return {"available": True, "session": None}
        except Exception as e:
            logger.error(f"Erreur check_slot_availability: {e}")
            return {"available": False, "error": str(e)} # Consider slot unavailable on error


    # --- Attendances ---
    def link_participants_to_session(self, session_id: int, group_id: int, cursor):
        """ Associe tous les participants d'un groupe à une session (dans attendances). CURSEUR REQUIS."""
        participants = self.get_participants_by_group(group_id) # Fetch participants outside loop if possible
        if not participants: return True # No participants to link

        sql_insert_attendance = """
            INSERT INTO attendances (session_id, participant_id, present)
            VALUES (%s, %s, FALSE)
            ON CONFLICT (session_id, participant_id) DO NOTHING
        """
        try:
            args_list = [(session_id, p['id']) for p in participants]
            cursor.executemany(sql_insert_attendance, args_list)
            return True
        except Exception as e:
            logger.error(f"Erreur link_participants_to_session {session_id} for group {group_id}: {e}")
            return False


    # --- Documents ---
    def save_document(self, doc_data: Dict[str, Any], cursor) -> Optional[int]:
        """ Enregistre un document. CURSEUR REQUIS. """
        sql = """
            INSERT INTO documents (filename, filetype, filesize, filedata, description, is_global, uploaded_by_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            doc_data['filename'],
            doc_data['filetype'],
            doc_data['filesize'],
            doc_data['filedata'], # Doit être psycopg2.Binary(bytes)
            doc_data.get('description'),
            doc_data.get('is_global', False),
            doc_data.get('uploaded_by_id') # Admin user ID
        )
        try:
            cursor.execute(sql, params)
            doc_id = cursor.fetchone()[0]
            return doc_id
        except Exception as e:
            logger.error(f"Erreur save_document '{doc_data.get('filename')}': {e}")
            return None

    def associate_document_to_session(self, document_id: int, session_id: int, cursor) -> bool:
        """ Associe un document à une session. CURSEUR REQUIS. """
        sql = """
            INSERT INTO session_documents (session_id, document_id)
            VALUES (%s, %s)
            ON CONFLICT (session_id, document_id) DO NOTHING
        """
        try:
            cursor.execute(sql, (session_id, document_id))
            return True # OK même si conflit (déjà associé)
        except Exception as e:
            logger.error(f"Erreur associate_document_to_session doc:{document_id} sess:{session_id}: {e}")
            return False

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute("SELECT id, filename, filetype, filesize, filedata, description, is_global, uploaded_by_id, created_at FROM documents WHERE id = %s", (document_id,))
                 return cursor.fetchone()
        except Exception as e:
             logger.error(f"Erreur get_document_by_id {document_id}: {e}")
             return None

    def get_documents_metadata_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        sql = """
            SELECT d.id, d.filename, d.filetype, d.filesize, d.description, d.is_global
            FROM documents d
            JOIN session_documents sd ON d.id = sd.document_id
            WHERE sd.session_id = %s
            ORDER BY d.filename
        """
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (session_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur get_documents_metadata_for_session {session_id}: {e}")
            return []

    def get_global_documents(self) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                 cursor.execute("SELECT id, filename, filetype, filesize, description FROM documents WHERE is_global = TRUE ORDER BY filename")
                 return cursor.fetchall()
        except Exception as e:
             logger.error(f"Erreur get_global_documents: {e}")
             return []

    # ... Delete/Update pour Documents ...

    # --- Activity Logs ---
    def add_activity_log(self, action: str, user_info: Optional[Dict]=None, details: Optional[Dict]=None, entity_type: Optional[str]=None, entity_id: Optional[int]=None, ip_address: Optional[str]=None, user_agent: Optional[str]=None):
        sql = """
            INSERT INTO activity_logs (action, user_info, details, entity_type, entity_id, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            action,
            json.dumps(user_info) if user_info else None,
            json.dumps(details) if details else None,
            entity_type,
            entity_id,
            ip_address,
            user_agent
        )
        try:
            # Commit immediately for logs
            with self.get_cursor(commit_on_exit=True) as cursor:
                cursor.execute(sql, params)
        except Exception as e:
            # Log error but don't stop the main process
            logger.error(f"Erreur add_activity_log ({action}): {e}")


    def get_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, action, user_info, details, entity_type, entity_id, ip_address, user_agent, created_at
            FROM activity_logs
            ORDER BY created_at DESC
            LIMIT %s
        """
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute(sql, (limit,))
                logs = cursor.fetchall()
                # Convert datetime for JSON compatibility if needed
                for log in logs:
                    if isinstance(log.get('created_at'), datetime.datetime):
                         log['created_at'] = log['created_at'].isoformat()
                return logs
        except Exception as e:
            logger.error(f"Erreur get_activity_logs: {e}")
            return []


    # --- Admin User ---
    def get_admin_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, username, password_hash, is_super_admin FROM admin_user WHERE username = %s", (username,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur get_admin_user_by_username {username}: {e}")
            return None

    def get_admin_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("SELECT id, username, password_hash, is_super_admin FROM admin_user WHERE id = %s", (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur get_admin_user_by_id {user_id}: {e}")
            return None

    # --- Stats (Exemple adapté) ---
    def get_dashboard_stats(self) -> Dict[str, Any]:
        stats = {'total_sessions': 0, 'total_participants': 0, 'sessions_by_department': {}, 'waiting_list_count': 0, 'new_feedback_count': 0}
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                # Total Sessions (non-canceled)
                cursor.execute("SELECT COUNT(*) as total FROM sessions WHERE status != 'canceled'")
                stats['total_sessions'] = cursor.fetchone()['total']

                # Total Participants (approx count from groups linked to non-canceled sessions)
                # This is complex, maybe just count unique participants in attendances?
                cursor.execute("""
                    SELECT COUNT(DISTINCT p.id) as total
                    FROM participants p
                    JOIN formation_groups g ON p.group_id = g.id
                    JOIN sessions s ON s.group_id = g.id
                    WHERE s.status != 'canceled'
                """)
                stats['total_participants'] = cursor.fetchone()['total'] # Approximatif

                # Sessions by Department
                cursor.execute("""
                    SELECT d.name, COUNT(s.id) as count
                    FROM sessions s
                    JOIN formation_groups g ON s.group_id = g.id
                    JOIN departments d ON g.department_id = d.id
                    WHERE s.status != 'canceled'
                    GROUP BY d.name
                """)
                stats['sessions_by_department'] = {row['name']: row['count'] for row in cursor.fetchall()}

                # Waiting List Count
                cursor.execute("SELECT COUNT(*) as total FROM waitlist WHERE status = 'waiting'")
                stats['waiting_list_count'] = cursor.fetchone()['total']

                # New Feedback Count
                cursor.execute("SELECT COUNT(*) as total FROM feedbacks WHERE status = 'new'")
                stats['new_feedback_count'] = cursor.fetchone()['total']

            return stats
        except Exception as e:
            logger.error(f"Erreur get_dashboard_stats: {e}")
            return stats # Retourner stats partielles ou par défaut

    # --- Add other necessary methods for waitlist, feedback, etc. ---

    def close_pool(self):
        """Ferme le pool de connexions"""
        if hasattr(self, 'connection_pool') and self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("Pool de connexions DB fermé.")
            except Exception as e:
                logger.error(f"Erreur fermeture pool connexion: {e}")

# --- Instance Creation ---
db_manager = None
try:
    db_manager = DatabaseManager()
except ConnectionError as e:
    logger.critical(f"CRITICAL: Echec init DatabaseManager - {e}")
    db_manager = None # S'assurer qu'il est None si échec
except Exception as e:
     logger.critical(f"CRITICAL: Erreur inattendue init DatabaseManager - {e}")
     db_manager = None

# Optional: Cleanup on exit
# import atexit
# def cleanup_db():
#     if db_manager:
#         db_manager.close_pool()
# atexit.register(cleanup_db)
