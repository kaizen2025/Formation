-- Script de migration de la base de données Anecoop Formation
-- Ce script restructure la base de données pour améliorer la cohérence et les performances

-- 1. Sauvegarde des données existantes
CREATE TABLE bookings_backup AS SELECT * FROM bookings;
CREATE TABLE waiting_list_backup AS SELECT * FROM waiting_list;
CREATE TABLE documents_backup AS SELECT * FROM documents;
CREATE TABLE document_bookings_backup AS SELECT * FROM document_bookings;
CREATE TABLE attendance_backup AS SELECT * FROM attendance;
CREATE TABLE activity_logs_backup AS SELECT * FROM activity_logs;
CREATE TABLE feedback_backup AS SELECT * FROM feedback;

-- 2. Création des nouvelles tables avec structure améliorée

-- Table des départements (anciennement services)
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    manager_name VARCHAR(100),
    contact_email VARCHAR(100),
    contact_phone VARCHAR(20),
    max_groups INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Table des modules de formation
CREATE TABLE formation_modules (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INTEGER DEFAULT 90,
    min_participants INTEGER DEFAULT 8,
    max_participants INTEGER DEFAULT 12,
    materials TEXT,
    objectives TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Table des groupes de formation
CREATE TABLE formation_groups (
    id SERIAL PRIMARY KEY,
    department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (department_id, name)
);

-- Table des sessions (anciennement bookings)
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES formation_groups(id) ON DELETE CASCADE,
    module_id INTEGER REFERENCES formation_modules(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    start_hour INTEGER NOT NULL,
    start_minutes INTEGER NOT NULL,
    duration_minutes INTEGER DEFAULT 90,
    location VARCHAR(100) DEFAULT 'Sur site',
    status VARCHAR(20) DEFAULT 'confirmed',
    additional_info TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (module_id, session_date, start_hour, start_minutes)
);

-- Table des participants
CREATE TABLE participants (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES formation_groups(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    department VARCHAR(100),
    position VARCHAR(100),
    notes TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Table des présences
CREATE TABLE attendances (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    participant_id INTEGER REFERENCES participants(id) ON DELETE CASCADE,
    present BOOLEAN DEFAULT FALSE,
    feedback TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (session_id, participant_id)
);

-- Table de la liste d'attente
CREATE TABLE waitlist (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20),
    department_id INTEGER REFERENCES departments(id),
    status VARCHAR(20) DEFAULT 'waiting',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Table des documents
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filetype VARCHAR(100) NOT NULL,
    filesize INTEGER NOT NULL,
    filedata BYTEA NOT NULL,
    document_type VARCHAR(50) DEFAULT 'attachment',
    description TEXT,
    is_global BOOLEAN DEFAULT FALSE,
    owner_email VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Table de liaison documents-sessions
CREATE TABLE session_documents (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, document_id)
);

-- Table de liaison documents-modules
CREATE TABLE module_documents (
    id SERIAL PRIMARY KEY,
    module_id INTEGER REFERENCES formation_modules(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (module_id, document_id)
);

-- Table des logs d'activité améliorée
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    user_info JSONB,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table du feedback
CREATE TABLE feedbacks (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    email VARCHAR(100),
    contact_name VARCHAR(100),
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'new',
    response TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 3. Migration des données
-- Remplir la table des départements
INSERT INTO departments (code, name, description)
VALUES 
('commerce-1', 'Commerce (Groupe 1)', 'Premier groupe du département Commerce'),
('commerce-2', 'Commerce (Groupe 2)', 'Second groupe du département Commerce'),
('comptabilite', 'Comptabilité', 'Département Comptabilité'),
('rh-qualite-marketing', 'RH / Qualité / Marketing', 'Départements RH, Qualité et Marketing');

-- Remplir la table des modules de formation
INSERT INTO formation_modules (code, name, description, duration_minutes)
VALUES
('teams-communication', 'Communiquer avec Teams', 'Apprendre à utiliser Microsoft Teams pour la communication d''équipe', 90),
('teams-sharepoint', 'Collaborer avec Teams/SharePoint', 'Utiliser Teams et SharePoint pour la collaboration documentaire', 90),
('task-management', 'Gérer les tâches d''équipe', 'Maîtriser les outils de gestion des tâches d''équipe', 90),
('onedrive-sharepoint', 'Gérer mes fichiers avec OneDrive/SharePoint', 'Organisation et gestion efficace des fichiers', 90);

-- Migration des données de réservation
-- Ceci est un exemple simplifié. L'implémentation complète nécessiterait des requêtes plus complexes
-- avec gestion des relations entre les nouvelles tables.

-- Fonction pour migrer les données
CREATE OR REPLACE FUNCTION migrate_booking_data() RETURNS void AS $$
DECLARE
    booking_record RECORD;
    new_group_id INTEGER;
    new_session_id INTEGER;
    participant_record RECORD;
BEGIN
    -- Pour chaque réservation existante
    FOR booking_record IN SELECT * FROM bookings_backup LOOP
        -- 1. Créer ou récupérer le groupe
        INSERT INTO formation_groups (
            department_id,
            name,
            contact_name,
            contact_email,
            contact_phone
        ) VALUES (
            (SELECT id FROM departments WHERE code = booking_record.service),
            'Groupe ' || booking_record.contact,
            booking_record.contact,
            booking_record.email,
            booking_record.phone
        )
        ON CONFLICT (department_id, name) DO UPDATE 
        SET contact_email = EXCLUDED.contact_email
        RETURNING id INTO new_group_id;
        
        -- 2. Créer la session
        INSERT INTO sessions (
            group_id,
            module_id,
            session_date,
            start_hour,
            start_minutes,
            additional_info,
            status
        ) VALUES (
            new_group_id,
            (SELECT id FROM formation_modules WHERE name = booking_record.formation_name),
            booking_record.booking_date,
            booking_record.hour,
            booking_record.minutes,
            booking_record.additional_info,
            booking_record.status
        )
        RETURNING id INTO new_session_id;
        
        -- 3. Migrer les participants
        IF booking_record.participants IS NOT NULL THEN
            FOR participant_record IN SELECT * FROM jsonb_array_elements(booking_record.participants) LOOP
                INSERT INTO participants (
                    group_id,
                    name,
                    email,
                    department
                ) VALUES (
                    new_group_id,
                    participant_record->>'name',
                    participant_record->>'email',
                    participant_record->>'department'
                );
            END LOOP;
        END IF;
        
        -- 4. Migrer les documents associés
        INSERT INTO session_documents (session_id, document_id)
        SELECT new_session_id, d.id
        FROM documents_backup d
        JOIN document_bookings_backup db ON d.id = db.document_id
        WHERE db.booking_id = booking_record.id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Exécuter la migration des données
SELECT migrate_booking_data();

-- 4. Création des indexes pour optimiser les performances

-- Index pour optimiser les recherches courantes
CREATE INDEX idx_sessions_date ON sessions(session_date);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_participants_group ON participants(group_id);
CREATE INDEX idx_participants_email ON participants(email);
CREATE INDEX idx_formation_groups_department ON formation_groups(department_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_global ON documents(is_global) WHERE is_global = TRUE;
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);

-- Index de recherche de texte pour les recherches
CREATE INDEX idx_participants_name_search ON participants USING gin(to_tsvector('french', name));
CREATE INDEX idx_documents_name_search ON documents USING gin(to_tsvector('french', name || ' ' || description));

-- 5. Création des triggers pour la maintenance des timestamps

-- Fonction pour mettre à jour le timestamp 'updated_at'
CREATE OR REPLACE FUNCTION update_modified_column() 
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Créer des triggers pour chaque table avec colonne updated_at
CREATE TRIGGER update_departments_timestamp BEFORE UPDATE
ON departments FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_formation_modules_timestamp BEFORE UPDATE
ON formation_modules FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_formation_groups_timestamp BEFORE UPDATE
ON formation_groups FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_sessions_timestamp BEFORE UPDATE
ON sessions FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_participants_timestamp BEFORE UPDATE
ON participants FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_attendances_timestamp BEFORE UPDATE
ON attendances FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_waitlist_timestamp BEFORE UPDATE
ON waitlist FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_documents_timestamp BEFORE UPDATE
ON documents FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

CREATE TRIGGER update_feedbacks_timestamp BEFORE UPDATE
ON feedbacks FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

-- 6. Création des vues pour simplifier les requêtes courantes

-- Vue des sessions avec informations détaillées
CREATE VIEW view_sessions_detailed AS
SELECT 
    s.id,
    s.session_date,
    s.start_hour,
    s.start_minutes,
    s.duration_minutes,
    s.status,
    s.additional_info,
    fm.name AS module_name,
    fm.description AS module_description,
    fg.name AS group_name,
    fg.contact_name,
    fg.contact_email,
    fg.contact_phone,
    d.name AS department_name,
    d.code AS department_code,
    (SELECT COUNT(*) FROM participants p WHERE p.group_id = fg.id) AS participant_count,
    s.created_at,
    s.updated_at
FROM 
    sessions s
JOIN 
    formation_modules fm ON s.module_id = fm.id
JOIN 
    formation_groups fg ON s.group_id = fg.id
JOIN 
    departments d ON fg.department_id = d.id;

-- Vue des participants avec leurs sessions
CREATE VIEW view_participants_sessions AS
SELECT 
    p.id AS participant_id,
    p.name AS participant_name,
    p.email AS participant_email,
    p.department AS participant_department,
    fg.id AS group_id,
    fg.name AS group_name,
    d.id AS department_id,
    d.name AS department_name,
    s.id AS session_id,
    s.session_date,
    s.start_hour,
    s.start_minutes,
    fm.name AS module_name,
    a.present AS attendance_status
FROM 
    participants p
JOIN 
    formation_groups fg ON p.group_id = fg.id
JOIN 
    departments d ON fg.department_id = d.id
JOIN 
    sessions s ON s.group_id = fg.id
JOIN 
    formation_modules fm ON s.module_id = fm.id
LEFT JOIN 
    attendances a ON a.session_id = s.id AND a.participant_id = p.id;

-- Vue des documents et leur utilisation
CREATE VIEW view_documents_usage AS
SELECT 
    d.id AS document_id,
    d.name,
    d.filename,
    d.filetype,
    d.filesize,
    d.document_type,
    d.description,
    d.is_global,
    s.id AS session_id,
    s.session_date,
    fm.name AS module_name,
    fg.name AS group_name,
    dep.name AS department_name
FROM 
    documents d
LEFT JOIN 
    session_documents sd ON d.id = sd.document_id
LEFT JOIN 
    sessions s ON sd.session_id = s.id
LEFT JOIN 
    formation_modules fm ON s.module_id = fm.id
LEFT JOIN 
    formation_groups fg ON s.group_id = fg.id
LEFT JOIN 
    departments dep ON fg.department_id = dep.id;

-- 7. Instructions pour les sauvegardes et restauration des données

COMMENT ON DATABASE anecoop_formation IS 'Système de réservation de formations Anecoop - Restructuré le 15/04/2025';

COMMENT ON TABLE departments IS 'Départements (anciennement services)';
COMMENT ON TABLE formation_modules IS 'Modules de formation disponibles';
COMMENT ON TABLE formation_groups IS 'Groupes de formation par département';
COMMENT ON TABLE sessions IS 'Sessions de formation planifiées';
COMMENT ON TABLE participants IS 'Liste des participants';
COMMENT ON TABLE attendances IS 'Suivi des présences aux formations';
COMMENT ON TABLE waitlist IS 'Liste d''attente pour les sessions complètes';
COMMENT ON TABLE documents IS 'Documents et ressources pédagogiques';
COMMENT ON TABLE activity_logs IS 'Journal des activités système';
COMMENT ON TABLE feedbacks IS 'Retours et commentaires des utilisateurs';

-- 8. Nettoyage (à exécuter seulement après validation complète de la migration)
-- DROP TABLE bookings_backup;
-- DROP TABLE waiting_list_backup;
-- DROP TABLE documents_backup;
-- DROP TABLE document_bookings_backup;
-- DROP TABLE attendance_backup;
-- DROP TABLE activity_logs_backup;
-- DROP TABLE feedback_backup;
-- DROP FUNCTION migrate_booking_data();

-- 9. Insertion de données de test (optionnel)
-- Cette section peut être ajoutée pour créer des données de test
-- dans le nouvel environnement