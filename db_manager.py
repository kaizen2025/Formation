import json
import logging
import datetime
import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

from config import DATABASE_URL

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de connexion et d'opérations sur la base de données"""

    def __init__(self):
        """Initialise la connexion à la base de données"""
        max_retries = 5 # Increased retries
        retry_delay = 3 # Seconds
        for attempt in range(max_retries):
            try:
                self.connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10, # Increased from 5
                    dsn=DATABASE_URL
                )
                logger.info("Pool de connexions à la base de données établi (min=1, max=10)")
                self.initialize_database()
                break # Success
            except psycopg2.OperationalError as e:
                logger.error(f"Erreur de connexion (Tentative {attempt + 1}/{max_retries}): {e}")
                if "too many connections" in str(e):
                     logger.warning("Le serveur de base de données signale trop de connexions. Vérifiez les limites du serveur ou réduisez maxconn.")
                if attempt == max_retries - 1:
                    logger.critical("Impossible de se connecter à la base de données après plusieurs tentatives.")
                    raise ConnectionError("Impossible d'établir la connexion à la base de données.") from e
                logger.info(f"Nouvelle tentative dans {retry_delay} secondes...")
                time.sleep(retry_delay)
            except Exception as e:
                 logger.critical(f"Erreur inattendue lors de l'initialisation du pool de connexion: {e}")
                 raise

    def get_connection(self):
        """Obtient une connexion depuis le pool"""
        try:
            return self.connection_pool.getconn()
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention d'une connexion du pool: {e}")
            raise ConnectionError("Impossible d'obtenir une connexion depuis le pool.") from e

    def release_connection(self, conn):
        """Libère une connexion et la renvoie au pool"""
        if conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Erreur lors de la libération de la connexion au pool: {e}")

    @contextmanager
    def get_cursor(self, use_dict_cursor=False):
        """
        Fournit un curseur de base de données géré par contexte.
        Acquiert une connexion depuis le pool et la libère automatiquement.
        Commits on success, rolls back on error.
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor_factory = RealDictCursor if use_dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            conn.commit()
        except Exception as e:
            logger.error(f"Erreur de base de données détectée: {e}. Annulation (rollback).")
            if conn:
                try:
                    conn.rollback()
                except Exception as rb_err:
                    logger.error(f"Erreur additionnelle lors du rollback: {rb_err}")
            raise # Re-raise the exception after rollback
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
            logger.error(f"Erreur lors du ping de la base de données: {e}")
            return False # Return False on error instead of raising

    def initialize_database(self):
        """Initialise les tables nécessaires si elles n'existent pas"""
        try:
            with self.get_cursor() as cursor:
                logger.info("Vérification/Création des tables...")

                # --- Bookings Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id SERIAL PRIMARY KEY,
                        service VARCHAR(50) NOT NULL,
                        contact VARCHAR(100) NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        phone VARCHAR(20),
                        formation_id VARCHAR(50) NOT NULL,
                        formation_name VARCHAR(100) NOT NULL,
                        booking_date DATE NOT NULL,
                        hour INTEGER NOT NULL,
                        minutes INTEGER NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        participants JSONB DEFAULT '[]'::jsonb,
                        additional_info TEXT,
                        status VARCHAR(20) DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'pending', 'canceled', 'waiting'))
                    );
                """)

                # --- Waiting List Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS waiting_list (
                        id SERIAL PRIMARY KEY,
                        booking_id INTEGER REFERENCES bookings(id) ON DELETE SET NULL,
                        service VARCHAR(50) NOT NULL,
                        contact VARCHAR(100) NOT NULL,
                        email VARCHAR(100) NOT NULL,
                        phone VARCHAR(20),
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'waiting' CHECK (status IN ('waiting', 'promoted', 'canceled', 'contacted'))
                    );
                """)

                # --- Activity Logs Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id SERIAL PRIMARY KEY,
                        action VARCHAR(50) NOT NULL,
                        user_info JSONB,
                        details JSONB,
                        ip_address VARCHAR(45),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # --- Feedback Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        type VARCHAR(50) NOT NULL,
                        message TEXT NOT NULL,
                        email VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'read', 'archived', 'resolved')),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # --- Documents Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        filetype VARCHAR(100) NOT NULL,
                        filesize INTEGER NOT NULL,
                        filedata BYTEA NOT NULL,
                        document_type VARCHAR(50) DEFAULT 'attachment',
                        description TEXT,
                        is_global BOOLEAN DEFAULT FALSE, -- Column definition
                        uploaded_by VARCHAR(100),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # --- ALTER TABLE to add is_global if it doesn't exist ---
                # This ensures compatibility if the table existed before the column was added
                logger.info("Vérification de la colonne 'is_global' dans la table 'documents'...")
                cursor.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = current_schema()
                            AND table_name = 'documents'
                            AND column_name = 'is_global'
                        ) THEN
                            ALTER TABLE documents ADD COLUMN is_global BOOLEAN DEFAULT FALSE;
                            RAISE NOTICE 'Colonne is_global ajoutée à la table documents.';
                        ELSE
                            RAISE NOTICE 'Colonne is_global existe déjà dans la table documents.';
                        END IF;
                    END $$;
                """)
                logger.info("Vérification de la colonne 'is_global' terminée.")


                # --- Document Bookings Join Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_bookings (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                        UNIQUE(document_id, booking_id)
                    );
                """)

                # --- Attendance Table ---
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        id SERIAL PRIMARY KEY,
                        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                        attendance_date DATE NOT NULL,
                        attendance_data JSONB NOT NULL,
                        comments TEXT,
                        recorded_by VARCHAR(100),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(booking_id, attendance_date)
                    );
                """)

                # --- Indexes ---
                logger.info("Vérification/Création des index...")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date_time ON bookings (booking_date, hour, minutes);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings (email);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_service ON bookings (service);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waiting_list (email);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_booking_id ON waiting_list (booking_id);")
                # Now this index creation should succeed
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_is_global ON documents (is_global);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_bookings_booking_id ON document_bookings (booking_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_bookings_document_id ON document_bookings (document_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_booking_id ON attendance (booking_id);")
                logger.info("Index initialisés/vérifiés avec succès.")

                logger.info("Initialisation de la base de données terminée avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des tables: {e}")
            raise # Re-raise to indicate failure

    # --- Rest of the DatabaseManager class methods (get_all_bookings, create_booking, etc.) ---
    # No changes needed in the other methods based on the error log provided.
    # Keep the improved versions from the previous response.

    # --- Booking Methods ---

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """Récupère toutes les réservations de la base de données"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.service, b.contact, b.email, b.phone,
                        b.formation_id, b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes,
                        TO_CHAR(b.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        b.participants, b.additional_info, b.status
                    FROM bookings b
                    ORDER BY b.booking_date, b.hour, b.minutes
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations: {e}")
            return []

    def get_bookings_by_service(self, service: str) -> List[Dict[str, Any]]:
        """Récupère les réservations pour un service spécifique"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.service, b.contact, b.email, b.phone,
                        b.formation_id, b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes,
                        TO_CHAR(b.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        b.participants, b.additional_info, b.status
                    FROM bookings b
                    WHERE b.service = %s
                    ORDER BY b.booking_date, b.hour, b.minutes
                """, (service,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations pour le service {service}: {e}")
            return []

    def get_bookings_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Récupère les réservations où l'utilisateur est responsable"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.service, b.contact, b.email, b.phone,
                        b.formation_id, b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes,
                        TO_CHAR(b.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        b.participants, b.additional_info, b.status
                    FROM bookings b
                    WHERE b.email = %s
                    ORDER BY b.booking_date, b.hour, b.minutes
                """, (email,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations pour l'email {email}: {e}")
            return []

    def get_bookings_by_participant_email(self, email: str) -> List[Dict[str, Any]]:
        """Récupère les réservations où l'utilisateur est participant"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.service, b.contact, b.email as contact_email, b.phone,
                        b.formation_id, b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes,
                        TO_CHAR(b.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        b.participants, b.additional_info, b.status
                    FROM bookings b
                    WHERE b.participants @> %s::jsonb
                    ORDER BY b.booking_date, b.hour, b.minutes
                """, (json.dumps([{'email': email}]),))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations pour le participant {email}: {e}")
            return []

    def get_booking_by_id(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une réservation par son ID"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        b.id, b.service, b.contact, b.email, b.phone,
                        b.formation_id, b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes,
                        TO_CHAR(b.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        b.participants, b.additional_info, b.status
                    FROM bookings b
                    WHERE b.id = %s
                """, (booking_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la réservation {booking_id}: {e}")
            return None

    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[int]:
        """Crée une nouvelle réservation et retourne son ID"""
        sql = """
            INSERT INTO bookings (
                service, contact, email, phone, formation_id, formation_name,
                booking_date, hour, minutes, participants, additional_info, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            booking_data['service'],
            booking_data['contact'],
            booking_data['email'],
            booking_data.get('phone'),
            booking_data['formation_id'],
            booking_data['formation_name'],
            booking_data['date'],
            booking_data['hour'],
            booking_data['minutes'],
            json.dumps(booking_data.get('participants', [])),
            booking_data.get('additional_info'),
            booking_data.get('status', 'confirmed')
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                booking_id = cursor.fetchone()[0]

            self.add_activity_log(
                'booking_created',
                {'email': booking_data['email'], 'service': booking_data['service']},
                {'booking_id': booking_id, 'formation': booking_data['formation_name']}
            )
            return booking_id
        except Exception as e:
            logger.error(f"Erreur lors de la création de la réservation: {e}")
            return None

    def update_booking(self, booking_id: int, booking_data: Dict[str, Any]) -> bool:
        """Met à jour une réservation existante"""
        sql = """
            UPDATE bookings
            SET
                service = %s, contact = %s, email = %s, phone = %s,
                formation_id = %s, formation_name = %s, booking_date = %s,
                hour = %s, minutes = %s, participants = %s,
                additional_info = %s, status = %s
            WHERE id = %s
        """
        params = (
            booking_data['service'],
            booking_data['contact'],
            booking_data['email'],
            booking_data.get('phone'),
            booking_data['formation_id'],
            booking_data['formation_name'],
            booking_data['date'],
            booking_data['hour'],
            booking_data['minutes'],
            json.dumps(booking_data.get('participants', [])),
            booking_data.get('additional_info'),
            booking_data.get('status', 'confirmed'),
            booking_id
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                updated_rows = cursor.rowcount

            if updated_rows > 0:
                self.add_activity_log(
                    'booking_updated',
                    {'email': booking_data['email'], 'service': booking_data['service']},
                    {'booking_id': booking_id, 'formation': booking_data['formation_name']}
                )
                return True
            else:
                logger.warning(f"Tentative de mise à jour de la réservation {booking_id} mais aucune ligne affectée.")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la réservation {booking_id}: {e}")
            return False

    def delete_booking(self, booking_id: int) -> bool:
        """Supprime une réservation"""
        try:
            booking_info = self.get_booking_by_id(booking_id)

            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
                deleted_rows = cursor.rowcount

            if deleted_rows > 0:
                if booking_info:
                     self.add_activity_log(
                        'booking_deleted',
                        {'service': booking_info['service'], 'email': booking_info['email']},
                        {'booking_id': booking_id, 'formation': booking_info['formation_name']}
                    )
                else:
                     self.add_activity_log('booking_deleted', None, {'booking_id': booking_id})
                logger.info(f"Réservation {booking_id} supprimée avec succès.")
                return True
            else:
                logger.warning(f"Tentative de suppression de la réservation {booking_id} mais aucune ligne affectée.")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la réservation {booking_id}: {e}")
            return False

    def check_slot_availability(self, date: str, hour: int, minutes: int) -> Dict[str, Any]:
        """Vérifie la disponibilité d'un créneau horaire et retourne des infos"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT b.id, b.service, b.formation_name, b.participants, COUNT(wl.id) as waitlist_count
                    FROM bookings b
                    LEFT JOIN waiting_list wl ON b.id = wl.booking_id AND wl.status = 'waiting'
                    WHERE b.booking_date = %s AND b.hour = %s AND b.minutes = %s
                    GROUP BY b.id, b.service, b.formation_name, b.participants
                """, (date, hour, minutes))
                booking = cursor.fetchone()

                if not booking:
                    return {"available": True, "booking": None, "waitlist_available": False, "waitlist_count": 0}

                from config import MAX_PARTICIPANTS, WAITLIST_CONFIG
                participants_count = len(booking.get('participants', []))
                waitlist_enabled = WAITLIST_CONFIG.get("enabled", False)
                waitlist_limit = WAITLIST_CONFIG.get("waitlist_limit", 0)
                current_waitlist_count = int(booking.get('waitlist_count', 0))

                waitlist_available = (
                    waitlist_enabled and
                    participants_count >= MAX_PARTICIPANTS and
                    current_waitlist_count < waitlist_limit
                )

                return {
                    "available": False,
                    "booking": booking,
                    "waitlist_available": waitlist_available,
                    "waitlist_count": current_waitlist_count
                }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du créneau {date} {hour}:{minutes}: {e}")
            return {"available": False, "error": str(e)}

    # --- Waitlist Methods ---

    def add_to_waiting_list(self, waitlist_data: Dict[str, Any]) -> Optional[int]:
        """Ajoute une personne à la liste d'attente pour une réservation"""
        sql = """
            INSERT INTO waiting_list (
                booking_id, service, contact, email, phone, status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            waitlist_data.get('booking_id'),
            waitlist_data['service'],
            waitlist_data['contact'],
            waitlist_data['email'],
            waitlist_data.get('phone'),
            waitlist_data.get('status', 'waiting')
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                waitlist_id = cursor.fetchone()[0]

            self.add_activity_log(
                'waitlist_added',
                {'email': waitlist_data['email'], 'service': waitlist_data['service']},
                {'booking_id': waitlist_data.get('booking_id'), 'waitlist_id': waitlist_id}
            )
            return waitlist_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout à la liste d'attente: {e}")
            return None

    def get_waiting_list(self) -> List[Dict[str, Any]]:
        """Récupère toute la liste d'attente"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        w.id, w.booking_id, w.service, w.contact, w.email, w.phone,
                        TO_CHAR(w.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        w.status,
                        COALESCE(b.formation_name, 'Formation supprimée') as formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes
                    FROM waiting_list w
                    LEFT JOIN bookings b ON w.booking_id = b.id
                    ORDER BY w.timestamp
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste d'attente: {e}")
            return []

    def get_waitlist_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Récupère la liste d'attente pour un email spécifique"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                     SELECT
                        w.id, w.booking_id, w.service, w.contact, w.email, w.phone,
                        TO_CHAR(w.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        w.status,
                        COALESCE(b.formation_name, 'Formation supprimée') as formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour, b.minutes
                    FROM waiting_list w
                    LEFT JOIN bookings b ON w.booking_id = b.id
                    WHERE w.email = %s
                    ORDER BY w.timestamp
                """, (email,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste d'attente pour l'email {email}: {e}")
            return []

    def remove_from_waitlist(self, waitlist_id: int) -> bool:
        """Supprime une entrée de la liste d'attente"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM waiting_list WHERE id = %s", (waitlist_id,))
                deleted_rows = cursor.rowcount
            if deleted_rows > 0:
                self.add_activity_log('waitlist_removed', None, {'waitlist_id': waitlist_id})
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'entrée de liste d'attente {waitlist_id}: {e}")
            return False

    def update_waitlist_status(self, waitlist_id: int, status: str) -> bool:
        """Met à jour le statut d'une entrée de liste d'attente"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("UPDATE waiting_list SET status = %s WHERE id = %s", (status, waitlist_id))
                updated_rows = cursor.rowcount
            if updated_rows > 0:
                 self.add_activity_log('waitlist_status_updated', None, {'waitlist_id': waitlist_id, 'new_status': status})
                 return True
            return False
        except Exception as e:
             logger.error(f"Erreur lors de la mise à jour du statut de l'entrée {waitlist_id}: {e}")
             return False

    # --- Attendance Methods ---

    def save_attendance(self, attendance_data: Dict[str, Any]) -> Optional[int]:
        """Enregistre ou met à jour les données de présence pour une réservation"""
        sql = """
            INSERT INTO attendance (
                booking_id, attendance_date, attendance_data, comments, recorded_by
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (booking_id, attendance_date) DO UPDATE SET
                attendance_data = EXCLUDED.attendance_data,
                comments = EXCLUDED.comments,
                recorded_by = EXCLUDED.recorded_by,
                timestamp = CURRENT_TIMESTAMP
            RETURNING id
        """
        params = (
            attendance_data['booking_id'],
            attendance_data['date'],
            json.dumps(attendance_data['attendance']),
            attendance_data.get('comments'),
            attendance_data.get('recorded_by')
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                attendance_id = cursor.fetchone()[0]

            self.add_activity_log(
                'attendance_recorded',
                {'recorded_by': attendance_data.get('recorded_by')},
                {'booking_id': attendance_data['booking_id'], 'date': attendance_data['date']}
            )
            return attendance_id
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des présences: {e}")
            return None

    def get_attendance_by_booking_id(self, booking_id: int) -> List[Dict[str, Any]]:
        """Récupère les données de présence pour une réservation"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, booking_id,
                        TO_CHAR(attendance_date, 'YYYY-MM-DD') as date,
                        attendance_data, comments, recorded_by,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM attendance
                    WHERE booking_id = %s
                    ORDER BY attendance_date DESC
                """, (booking_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des présences pour la réservation {booking_id}: {e}")
            return []

    # --- Activity Log Methods ---

    def add_activity_log(self, action: str, user_info: Optional[Dict[str, Any]],
                         details: Optional[Dict[str, Any]], ip_address: Optional[str] = None) -> Optional[int]:
        """Ajoute une entrée dans les logs d'activité"""
        sql = """
            INSERT INTO activity_logs (action, user_info, details, ip_address)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = (
            action,
            json.dumps(user_info) if user_info else None,
            json.dumps(details) if details else None,
            ip_address
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                log_id = cursor.fetchone()[0]
            return log_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du log d'activité ({action}): {e}")
            return None

    def get_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les logs d'activité"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, action, user_info, details, ip_address,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM activity_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des logs d'activité: {e}")
            return []

    # --- Feedback Methods ---

    def save_feedback(self, feedback_data: Dict[str, Any]) -> Optional[int]:
        """Enregistre un feedback utilisateur"""
        sql = """
            INSERT INTO feedback (type, message, email, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = (
            feedback_data.get('type', 'other'),
            feedback_data['message'],
            feedback_data.get('email'),
            feedback_data.get('status', 'new')
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                feedback_id = cursor.fetchone()[0]

            self.add_activity_log(
                'feedback_submitted',
                {'email': feedback_data.get('email')},
                {'feedback_id': feedback_id, 'type': feedback_data.get('type')}
            )
            return feedback_id
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du feedback: {e}")
            return None

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Récupère tous les feedbacks"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, type, message, email, status,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM feedback
                    ORDER BY timestamp DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des feedbacks: {e}")
            return []

    def update_feedback_status(self, feedback_id: int, status: str) -> bool:
        """Met à jour le statut d'un feedback"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("UPDATE feedback SET status = %s WHERE id = %s", (status, feedback_id))
                updated_rows = cursor.rowcount
            if updated_rows > 0:
                 self.add_activity_log('feedback_status_updated', None, {'feedback_id': feedback_id, 'new_status': status})
                 return True
            return False
        except Exception as e:
             logger.error(f"Erreur lors de la mise à jour du statut du feedback {feedback_id}: {e}")
             return False

    # --- Document Methods ---

    def save_document(self, document_data: Dict[str, Any]) -> Optional[int]:
        """Enregistre un document (global ou non)"""
        sql = """
            INSERT INTO documents (
                filename, filetype, filesize, filedata,
                document_type, description, is_global, uploaded_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            document_data['filename'],
            document_data['filetype'],
            document_data['filesize'],
            document_data['filedata'], # Should be psycopg2.Binary(file_bytes)
            document_data.get('document_type', 'attachment'),
            document_data.get('description', ''),
            document_data.get('is_global', False),
            document_data.get('uploaded_by')
        )
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                document_id = cursor.fetchone()[0]

            self.add_activity_log(
                'document_uploaded',
                {'uploaded_by': document_data.get('uploaded_by')},
                {'document_id': document_id, 'filename': document_data['filename']}
            )
            return document_id
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du document: {e}")
            return None

    def associate_document_to_booking(self, document_id: int, booking_id: int) -> bool:
        """Associe un document existant à une réservation"""
        sql = """
            INSERT INTO document_bookings (document_id, booking_id)
            VALUES (%s, %s)
            ON CONFLICT (document_id, booking_id) DO NOTHING
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (document_id, booking_id))
                inserted_rows = cursor.rowcount
            self.add_activity_log(
                'document_associated',
                None,
                {'document_id': document_id, 'booking_id': booking_id, 'newly_inserted': inserted_rows > 0}
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'association du document {document_id} à la réservation {booking_id}: {e}")
            return False

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un document par son ID (inclut les données binaires)"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, filename, filetype, filesize, filedata,
                        document_type, description, is_global, uploaded_by,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM documents
                    WHERE id = %s
                """, (document_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du document {document_id}: {e}")
            return None

    def get_documents_metadata_by_booking_id(self, booking_id: int) -> List[Dict[str, Any]]:
        """Récupère les métadonnées des documents associés à une réservation (sans les données binaires)"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        d.id, d.filename, d.filetype, d.filesize,
                        d.document_type, d.description, d.is_global, d.uploaded_by,
                        TO_CHAR(d.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM documents d
                    JOIN document_bookings db ON d.id = db.document_id
                    WHERE db.booking_id = %s
                    ORDER BY d.timestamp DESC
                """, (booking_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées des documents pour la réservation {booking_id}: {e}")
            return []

    def get_global_documents(self) -> List[Dict[str, Any]]:
        """Récupère tous les documents globaux (métadonnées uniquement)"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, filename, filetype, filesize,
                        document_type, description, uploaded_by,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM documents
                    WHERE is_global = TRUE
                    ORDER BY timestamp DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des documents globaux: {e}")
            return []

    def get_all_documents_metadata(self) -> List[Dict[str, Any]]:
        """Récupère les métadonnées de tous les documents"""
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    SELECT
                        id, filename, filetype, filesize,
                        document_type, description, is_global, uploaded_by,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM documents
                    ORDER BY timestamp DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de tous les documents: {e}")
            return []

    def delete_document(self, document_id: int) -> bool:
        """Supprime un document"""
        try:
            doc_info = self.get_document_by_id(document_id)

            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
                deleted_rows = cursor.rowcount

            if deleted_rows > 0:
                filename = doc_info['filename'] if doc_info else 'Unknown'
                self.add_activity_log('document_deleted', None, {'document_id': document_id, 'filename': filename})
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du document {document_id}: {e}")
            return False

    # --- Dashboard Stats ---

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtient des statistiques pour le tableau de bord admin"""
        stats = {
            'total_bookings': 0, 'total_participants': 0, 'bookings_by_service': {},
            'bookings_by_month': {}, 'waiting_list_count': 0, 'bookings_by_formation': {},
            'total_documents': 0, 'global_documents': 0, 'new_feedback_count': 0,
            'bookings_trend': 0
        }
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                cursor.execute("""
                    WITH BookingCounts AS (
                        SELECT COUNT(*) as total FROM bookings
                    ), ParticipantCounts AS (
                        SELECT COALESCE(SUM(jsonb_array_length(participants)), 0) as total FROM bookings
                    ), BookingsByService AS (
                        SELECT service, COUNT(*) as count FROM bookings GROUP BY service
                    ), BookingsByMonth AS (
                        SELECT EXTRACT(MONTH FROM booking_date) as month, COUNT(*) as count FROM bookings GROUP BY month
                    ), WaitlistCounts AS (
                        SELECT COUNT(*) as total FROM waiting_list WHERE status = 'waiting'
                    ), BookingsByFormation AS (
                        SELECT formation_name, COUNT(*) as count FROM bookings GROUP BY formation_name
                    ), DocumentCounts AS (
                        SELECT COUNT(*) as total FROM documents
                    ), GlobalDocCounts AS (
                        SELECT COUNT(*) as total FROM documents WHERE is_global = TRUE
                    ), NewFeedbackCounts AS (
                        SELECT COUNT(*) as total FROM feedback WHERE status = 'new'
                    ), BookingsLastMonth AS (
                         SELECT COUNT(*) as count FROM bookings
                         WHERE timestamp >= date_trunc('month', current_date - interval '1 month')
                         AND timestamp < date_trunc('month', current_date)
                    ), BookingsThisMonth AS (
                         SELECT COUNT(*) as count FROM bookings
                         WHERE timestamp >= date_trunc('month', current_date)
                    )
                    SELECT
                        (SELECT total FROM BookingCounts) as total_bookings,
                        (SELECT total FROM ParticipantCounts) as total_participants,
                        (SELECT jsonb_object_agg(service, count) FROM BookingsByService) as bookings_by_service,
                        (SELECT jsonb_object_agg(month::text, count) FROM BookingsByMonth) as bookings_by_month,
                        (SELECT total FROM WaitlistCounts) as waiting_list_count,
                        (SELECT jsonb_object_agg(formation_name, count) FROM BookingsByFormation) as bookings_by_formation,
                        (SELECT total FROM DocumentCounts) as total_documents,
                        (SELECT total FROM GlobalDocCounts) as global_documents,
                        (SELECT total FROM NewFeedbackCounts) as new_feedback_count,
                        (SELECT count FROM BookingsLastMonth) as bookings_last_month,
                        (SELECT count FROM BookingsThisMonth) as bookings_this_month
                """)
                result = cursor.fetchone()

                if result:
                    stats['total_bookings'] = result.get('total_bookings', 0)
                    stats['total_participants'] = int(result.get('total_participants', 0))
                    stats['bookings_by_service'] = result.get('bookings_by_service', {}) or {}
                    stats['bookings_by_month'] = {int(k): v for k, v in (result.get('bookings_by_month', {}) or {}).items()}
                    stats['waiting_list_count'] = result.get('waiting_list_count', 0)
                    stats['bookings_by_formation'] = result.get('bookings_by_formation', {}) or {}
                    stats['total_documents'] = result.get('total_documents', 0)
                    stats['global_documents'] = result.get('global_documents', 0)
                    stats['new_feedback_count'] = result.get('new_feedback_count', 0)

                    last_month = result.get('bookings_last_month', 0)
                    this_month = result.get('bookings_this_month', 0)
                    if last_month > 0:
                        stats['bookings_trend'] = round(((this_month - last_month) / last_month) * 100)
                    elif this_month > 0:
                         stats['bookings_trend'] = 100
                    else:
                         stats['bookings_trend'] = 0

            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return stats

    # --- Search Method ---
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Recherche globale dans les réservations, participants, documents"""
        results = []
        search_term = f"%{query}%"
        try:
            with self.get_cursor(use_dict_cursor=True) as cursor:
                # Search Bookings
                cursor.execute("""
                    SELECT id, formation_name as title, TO_CHAR(booking_date, 'YYYY-MM-DD') as date,
                           service as context, 'booking' as type
                    FROM bookings
                    WHERE formation_name ILIKE %s OR contact ILIKE %s OR email ILIKE %s OR service ILIKE %s
                    LIMIT 10
                """, (search_term, search_term, search_term, search_term))
                results.extend(cursor.fetchall())

                # Search Participants
                cursor.execute("""
                    SELECT b.id as booking_id, p.name as title, b.formation_name as context, 'participant' as type
                    FROM bookings b, jsonb_to_recordset(b.participants) AS p(name text, email text, department text)
                    WHERE p.name ILIKE %s OR p.email ILIKE %s OR p.department ILIKE %s
                    LIMIT 10
                """, (search_term, search_term, search_term))
                results.extend(cursor.fetchall())

                # Search Documents
                cursor.execute("""
                    SELECT id, filename as title, document_type as context, 'document' as type
                    FROM documents
                    WHERE filename ILIKE %s OR description ILIKE %s
                    LIMIT 10
                """, (search_term, search_term))
                results.extend(cursor.fetchall())

            # Add URLs (example)
            for result in results:
                if result['type'] == 'booking':
                    result['url'] = f"/admin/booking/{result['id']}"
                elif result['type'] == 'participant':
                     result['url'] = f"/admin/participants?search={result['title']}"
                elif result['type'] == 'document':
                     result['url'] = f"/admin/documents?search={result['title']}"

            return results

        except Exception as e:
            logger.error(f"Erreur lors de la recherche globale pour '{query}': {e}")
            return []

    def close_pool(self):
        """Ferme le pool de connexions"""
        if hasattr(self, 'connection_pool') and self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("Pool de connexions fermé.")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture du pool de connexions: {e}")


# --- Instance Creation and Cleanup ---
db_manager = None
try:
    db_manager = DatabaseManager()
except ConnectionError as e:
    logger.critical(f"CRITICAL: Failed to initialize DatabaseManager - {e}")
except Exception as e:
     logger.critical(f"CRITICAL: Unexpected error initializing DatabaseManager - {e}")

# Optional: Add a cleanup function for application shutdown
# import atexit
# def cleanup_db():
#     if db_manager:
#         db_manager.close_pool()
# atexit.register(cleanup_db)