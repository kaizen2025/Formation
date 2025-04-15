"""
Gestionnaire de base de données pour l'application de réservation des formations Anecoop
"""

import json
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple

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
        try:
            # Créer un pool de connexions pour une meilleure performance
            self.connection_pool = pool.ThreadedConnectionPool(1, 20, DATABASE_URL)
            logger.info("Connexion à la base de données établie")
            
            # Initialiser les tables si elles n'existent pas
            self.initialize_database()
        except Exception as e:
            logger.error(f"Erreur lors de la connexion à la base de données: {e}")
            raise
    
    def get_connection(self):
        """Obtient une connexion depuis le pool"""
        return self.connection_pool.getconn()
    
    def release_connection(self, conn):
        """Libère une connexion et la renvoie au pool"""
        self.connection_pool.putconn(conn)
    
    def initialize_database(self):
        """Initialise les tables nécessaires si elles n'existent pas"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Création des tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(50) NOT NULL,
                    contact VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    phone VARCHAR(20),
                    formation_id VARCHAR(20) NOT NULL,
                    formation_name VARCHAR(100) NOT NULL,
                    booking_date DATE NOT NULL,
                    hour INTEGER NOT NULL,
                    minutes INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    participants JSONB DEFAULT '[]'::jsonb,
                    documents JSONB DEFAULT '[]'::jsonb,
                    additional_info TEXT,
                    status VARCHAR(20) DEFAULT 'confirmed'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS waiting_list (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
                    service VARCHAR(50) NOT NULL,
                    contact VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    phone VARCHAR(20),
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'waiting'
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(50) NOT NULL,
                    user_info JSONB,
                    details JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    email VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'new',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    filetype VARCHAR(100) NOT NULL,
                    filesize INTEGER NOT NULL,
                    filedata BYTEA NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Tables initialisées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des tables: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """Récupère toutes les réservations de la base de données"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        service,
                        contact,
                        email,
                        phone,
                        formation_id,
                        formation_name,
                        TO_CHAR(booking_date, 'YYYY-MM-DD') as date,
                        hour,
                        minutes,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        participants,
                        documents,
                        additional_info,
                        status
                    FROM bookings
                    ORDER BY booking_date, hour, minutes
                """)
                bookings = cursor.fetchall()
                return bookings
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations: {e}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_bookings_by_service(self, service: str) -> List[Dict[str, Any]]:
        """Récupère les réservations pour un service spécifique"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        service,
                        contact,
                        email,
                        phone,
                        formation_id,
                        formation_name,
                        TO_CHAR(booking_date, 'YYYY-MM-DD') as date,
                        hour,
                        minutes,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        participants,
                        documents,
                        additional_info,
                        status
                    FROM bookings
                    WHERE service = %s
                    ORDER BY booking_date, hour, minutes
                """, (service,))
                bookings = cursor.fetchall()
                return bookings
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations pour le service {service}: {e}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_booking_by_id(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une réservation par son ID"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        service,
                        contact,
                        email,
                        phone,
                        formation_id,
                        formation_name,
                        TO_CHAR(booking_date, 'YYYY-MM-DD') as date,
                        hour,
                        minutes,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        participants,
                        documents,
                        additional_info,
                        status
                    FROM bookings
                    WHERE id = %s
                """, (booking_id,))
                booking = cursor.fetchone()
                return booking
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la réservation {booking_id}: {e}")
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[int]:
        """Crée une nouvelle réservation et retourne son ID"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO bookings (
                        service, contact, email, phone, formation_id, formation_name,
                        booking_date, hour, minutes, participants, documents, additional_info, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
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
                    json.dumps(booking_data.get('documents', [])),
                    booking_data.get('additional_info'),
                    booking_data.get('status', 'confirmed')
                ))
                booking_id = cursor.fetchone()[0]
                conn.commit()
                
                # Ajouter un log d'activité
                self.add_activity_log(
                    'booking_created',
                    {'email': booking_data['email'], 'service': booking_data['service']},
                    {'booking_id': booking_id, 'formation': booking_data['formation_name']}
                )
                
                return booking_id
        except Exception as e:
            logger.error(f"Erreur lors de la création de la réservation: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def update_booking(self, booking_id: int, booking_data: Dict[str, Any]) -> bool:
        """Met à jour une réservation existante"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE bookings 
                    SET 
                        service = %s,
                        contact = %s,
                        email = %s,
                        phone = %s,
                        formation_id = %s,
                        formation_name = %s,
                        booking_date = %s,
                        hour = %s,
                        minutes = %s,
                        participants = %s,
                        documents = %s,
                        additional_info = %s,
                        status = %s
                    WHERE id = %s
                """, (
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
                    json.dumps(booking_data.get('documents', [])),
                    booking_data.get('additional_info'),
                    booking_data.get('status', 'confirmed'),
                    booking_id
                ))
                conn.commit()
                
                # Ajouter un log d'activité
                self.add_activity_log(
                    'booking_updated',
                    {'email': booking_data['email'], 'service': booking_data['service']},
                    {'booking_id': booking_id, 'formation': booking_data['formation_name']}
                )
                
                return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la réservation {booking_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def delete_booking(self, booking_id: int) -> bool:
        """Supprime une réservation"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
                conn.commit()
                
                # Ajouter un log d'activité
                self.add_activity_log(
                    'booking_deleted',
                    None,
                    {'booking_id': booking_id}
                )
                
                return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la réservation {booking_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def check_slot_availability(self, date: str, hour: int, minutes: int) -> Dict[str, Any]:
        """Vérifie la disponibilité d'un créneau horaire et retourne des infos"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, service, formation_name, participants
                    FROM bookings
                    WHERE booking_date = %s AND hour = %s AND minutes = %s
                """, (date, hour, minutes))
                booking = cursor.fetchone()
                
                if not booking:
                    return {"available": True, "booking": None, "waiting_list_available": False}
                
                # Vérifier si des places sont disponibles sur la liste d'attente
                participants_count = len(booking.get('participants', []))
                waiting_list_available = participants_count < MAX_PARTICIPANTS
                
                return {
                    "available": False,
                    "booking": booking,
                    "waiting_list_available": waiting_list_available
                }
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du créneau {date} {hour}:{minutes}: {e}")
            return {"available": False, "error": str(e)}
        finally:
            if conn:
                self.release_connection(conn)
    
    def add_to_waiting_list(self, waitlist_data: Dict[str, Any]) -> Optional[int]:
        """Ajoute une personne à la liste d'attente pour une réservation"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO waiting_list (
                        booking_id, service, contact, email, phone, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    waitlist_data['booking_id'],
                    waitlist_data['service'],
                    waitlist_data['contact'],
                    waitlist_data['email'],
                    waitlist_data.get('phone'),
                    waitlist_data.get('status', 'waiting')
                ))
                waitlist_id = cursor.fetchone()[0]
                conn.commit()
                
                # Ajouter un log d'activité
                self.add_activity_log(
                    'waitlist_added',
                    {'email': waitlist_data['email'], 'service': waitlist_data['service']},
                    {'booking_id': waitlist_data['booking_id']}
                )
                
                return waitlist_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout à la liste d'attente: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_waiting_list(self) -> List[Dict[str, Any]]:
        """Récupère toute la liste d'attente"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        w.id,
                        w.booking_id,
                        w.service,
                        w.contact,
                        w.email,
                        w.phone,
                        TO_CHAR(w.timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp,
                        w.status,
                        b.formation_name,
                        TO_CHAR(b.booking_date, 'YYYY-MM-DD') as date,
                        b.hour,
                        b.minutes
                    FROM waiting_list w
                    JOIN bookings b ON w.booking_id = b.id
                    ORDER BY w.timestamp
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste d'attente: {e}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def add_activity_log(self, action: str, user_info: Optional[Dict[str, Any]], 
                         details: Optional[Dict[str, Any]]) -> Optional[int]:
        """Ajoute une entrée dans les logs d'activité"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activity_logs (action, user_info, details)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    action,
                    json.dumps(user_info) if user_info else None,
                    json.dumps(details) if details else None
                ))
                log_id = cursor.fetchone()[0]
                conn.commit()
                return log_id
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du log d'activité: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les logs d'activité"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        action,
                        user_info,
                        details,
                        TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as timestamp
                    FROM activity_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des logs d'activité: {e}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def save_feedback(self, feedback_data: Dict[str, Any]) -> Optional[int]:
        """Enregistre un feedback utilisateur"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO feedback (type, message, email)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    feedback_data['type'],
                    feedback_data['message'],
                    feedback_data.get('email')
                ))
                feedback_id = cursor.fetchone()[0]
                conn.commit()
                return feedback_id
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du feedback: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def save_document(self, document_data: Dict[str, Any]) -> Optional[int]:
        """Enregistre un document pour une réservation"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO documents (booking_id, filename, filetype, filesize, filedata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    document_data['booking_id'],
                    document_data['filename'],
                    document_data['filetype'],
                    document_data['filesize'],
                    document_data['filedata']
                ))
                document_id = cursor.fetchone()[0]
                conn.commit()
                return document_id
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du document: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtient des statistiques pour le tableau de bord admin"""
        conn = None
        try:
            conn = self.get_connection()
            stats = {}
            
            with conn.cursor() as cursor:
                # Nombre total de réservations
                cursor.execute("SELECT COUNT(*) FROM bookings")
                stats['total_bookings'] = cursor.fetchone()[0]
                
                # Nombre total de participants
                cursor.execute("""
                    SELECT SUM(jsonb_array_length(participants))
                    FROM bookings
                """)
                participants_result = cursor.fetchone()[0]
                stats['total_participants'] = participants_result if participants_result else 0
                
                # Réservations par service
                cursor.execute("""
                    SELECT service, COUNT(*) as count
                    FROM bookings
                    GROUP BY service
                """)
                stats['bookings_by_service'] = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Réservations par mois
                cursor.execute("""
                    SELECT 
                        EXTRACT(MONTH FROM booking_date) as month,
                        COUNT(*) as count
                    FROM bookings
                    GROUP BY month
                    ORDER BY month
                """)
                stats['bookings_by_month'] = {int(row[0]): row[1] for row in cursor.fetchall()}
                
                # Personnes en liste d'attente
                cursor.execute("SELECT COUNT(*) FROM waiting_list")
                stats['waiting_list_count'] = cursor.fetchone()[0]
                
                # Réservations par formation
                cursor.execute("""
                    SELECT formation_name, COUNT(*) as count
                    FROM bookings
                    GROUP BY formation_name
                """)
                stats['bookings_by_formation'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
        finally:
            if conn:
                self.release_connection(conn)


# Créer une instance globale
db_manager = DatabaseManager()