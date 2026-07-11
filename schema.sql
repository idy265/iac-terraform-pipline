-- Schéma SQL de la plateforme de gestion des incidents et demandes de travaux.
-- Ce fichier documente le modèle relationnel ; en pratique les tables sont
-- créées via SQLAlchemy (voir app/models.py et db.create_all()).

CREATE TABLE roles (
    id      INTEGER PRIMARY KEY,
    nom     VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE sites (
    id      INTEGER PRIMARY KEY,
    nom     VARCHAR(120) NOT NULL,
    adresse VARCHAR(255)
);

CREATE TABLE emplacements (
    id       INTEGER PRIMARY KEY,
    site_id  INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE, -- Règle 14
    zone     VARCHAR(120) NOT NULL
);

CREATE TABLE equipements (
    id             INTEGER PRIMARY KEY,
    nom            VARCHAR(150) NOT NULL,
    code_barre     VARCHAR(80),
    numero_serie   VARCHAR(120),
    type_equipement VARCHAR(80),                    -- PC Portable, Imprimante, Ascenseur, Chaudière...
    emplacement_id INTEGER REFERENCES emplacements(id) ON DELETE CASCADE,
    statut         VARCHAR(40) NOT NULL DEFAULT 'Fonctionnel' -- Fonctionnel / En panne / En maintenance
);

CREATE TABLE categories (
    id              INTEGER PRIMARY KEY,
    nom             VARCHAR(120) NOT NULL,
    type_plateforme VARCHAR(40) NOT NULL,          -- Informatique / Bâtiment (Règle 3)
    parent_id       INTEGER REFERENCES categories(id)
);

CREATE TABLE utilisateurs (
    id            INTEGER PRIMARY KEY,
    nom           VARCHAR(120) NOT NULL,
    prenom        VARCHAR(120),
    email         VARCHAR(255) NOT NULL UNIQUE,
    telephone     VARCHAR(40),
    password_hash VARCHAR(255) NOT NULL,
    role_id       INTEGER NOT NULL REFERENCES roles(id),
    site_id       INTEGER REFERENCES sites(id),
    specialite    VARCHAR(40)                        -- spécialité du technicien (Règle 3)
);

CREATE TABLE declarations (
    id             INTEGER PRIMARY KEY,
    titre          VARCHAR(200) NOT NULL,
    description    TEXT,
    statut         VARCHAR(40) NOT NULL DEFAULT 'En attente', -- Règle 5
    priorite       VARCHAR(40) NOT NULL DEFAULT 'Moyenne',
    date_creation  DATETIME NOT NULL,
    date_resolution DATETIME,                                 -- Règle 9
    declarant_id   INTEGER NOT NULL REFERENCES utilisateurs(id), -- Règle 13 (pas de cascade)
    technicien_id  INTEGER REFERENCES utilisateurs(id),       -- Règle 7
    categorie_id   INTEGER NOT NULL REFERENCES categories(id), -- Règle 6
    emplacement_id INTEGER NOT NULL REFERENCES emplacements(id), -- Règle 6
    equipement_id  INTEGER REFERENCES equipements(id)          -- équipement concerné (optionnel)
);

CREATE TABLE commentaires (
    id               INTEGER PRIMARY KEY,
    declaration_id   INTEGER NOT NULL REFERENCES declarations(id),
    auteur_id        INTEGER NOT NULL REFERENCES utilisateurs(id),
    message          TEXT NOT NULL,
    date_publication DATETIME NOT NULL,
    est_interne      BOOLEAN NOT NULL DEFAULT 0                -- notes internes techniciens
);

CREATE TABLE pieces_jointes (
    id                  INTEGER PRIMARY KEY,
    declaration_id      INTEGER NOT NULL REFERENCES declarations(id),
    nom_fichier         VARCHAR(255) NOT NULL,
    url_stockage        VARCHAR(512) NOT NULL,
    date_telechargement DATETIME NOT NULL
);

CREATE TABLE historique_statuts (
    id                  INTEGER PRIMARY KEY,
    declaration_id      INTEGER NOT NULL REFERENCES declarations(id),
    statut_precedent    VARCHAR(40),
    nouveau_statut      VARCHAR(40) NOT NULL,
    modifie_par_user_id INTEGER REFERENCES utilisateurs(id),
    date_changement     DATETIME NOT NULL
);

CREATE TABLE alertes (
    id              INTEGER PRIMARY KEY,
    destinataire_id INTEGER NOT NULL REFERENCES utilisateurs(id), -- technicien / admin / déclarant averti
    declaration_id  INTEGER NOT NULL REFERENCES declarations(id),
    type_alerte     VARCHAR(40) NOT NULL,                         -- nouvelle_declaration / nouveau_commentaire
    message         VARCHAR(255) NOT NULL,
    lu              BOOLEAN NOT NULL DEFAULT 0,
    date_creation   DATETIME NOT NULL
);
