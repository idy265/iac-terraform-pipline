"""SQLAlchemy models for the incident / work-order management platform.

The schema follows the specification: users and roles, sites and precise
locations, categories, declarations (the ticket), comments, attachments and a
status history used to measure processing times (SLA).
"""

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .constants import (
    EQUIP_FONCTIONNEL,
    PRIORITE_MOYENNE,
    ROLE_DEMANDEUR,
    STATUT_EN_ATTENTE,
)
from .extensions import db


class Role(db.Model):
    """Defines permissions on the platform (Demandeur, Technicien, Admin)."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), unique=True, nullable=False)

    utilisateurs = db.relationship("Utilisateur", back_populates="role")

    def __repr__(self):
        return f"<Role {self.nom}>"


class Site(db.Model):
    """A building / physical site."""

    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    adresse = db.Column(db.String(255))

    # Rule 14: deleting a site cascades to its locations.
    emplacements = db.relationship(
        "Emplacement",
        back_populates="site",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Site {self.nom}>"


class Emplacement(db.Model):
    """A precise location (zone) inside a site."""

    __tablename__ = "emplacements"

    id = db.Column(db.Integer, primary_key=True)
    # Rule 14: a location must belong to an existing site.
    site_id = db.Column(
        db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    zone = db.Column(db.String(120), nullable=False)

    site = db.relationship("Site", back_populates="emplacements")
    equipements = db.relationship(
        "Equipement",
        back_populates="emplacement",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Emplacement {self.zone}>"


class Equipement(db.Model):
    """A tracked asset (PC, printer, elevator, boiler, ...) that can break."""

    __tablename__ = "equipements"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    code_barre = db.Column(db.String(80))
    numero_serie = db.Column(db.String(120))
    type_equipement = db.Column(db.String(80))
    emplacement_id = db.Column(
        db.Integer, db.ForeignKey("emplacements.id", ondelete="CASCADE")
    )
    statut = db.Column(db.String(40), nullable=False, default=EQUIP_FONCTIONNEL)

    emplacement = db.relationship("Emplacement", back_populates="equipements")

    def __repr__(self):
        return f"<Equipement {self.nom} [{self.statut}]>"


class Categorie(db.Model):
    """The nature of the problem, used to route to the right team (Rule 3)."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    # "Informatique" or "Bâtiment" -- used to filter incidents per team.
    type_plateforme = db.Column(db.String(40), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"))

    parent = db.relationship("Categorie", remote_side=[id], backref="sous_categories")

    def __repr__(self):
        return f"<Categorie {self.nom} ({self.type_plateforme})>"


class Utilisateur(db.Model):
    """Anyone who accesses the application (requester, technician, admin)."""

    __tablename__ = "utilisateurs"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    prenom = db.Column(db.String(120))
    email = db.Column(db.String(255), unique=True, nullable=False)
    telephone = db.Column(db.String(40))
    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"))
    # For technicians: the platform they are allowed to handle (Rule 3).
    specialite = db.Column(db.String(40))

    role = db.relationship("Role", back_populates="utilisateurs")
    site = db.relationship("Site")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        from .constants import ROLE_ADMIN

        return self.role is not None and self.role.nom == ROLE_ADMIN

    @property
    def is_technicien(self):
        from .constants import ROLE_TECHNICIEN

        return self.role is not None and self.role.nom == ROLE_TECHNICIEN

    @property
    def is_demandeur(self):
        return self.role is not None and self.role.nom == ROLE_DEMANDEUR

    def __repr__(self):
        return f"<Utilisateur {self.email}>"


class Declaration(db.Model):
    """The incident ticket -- the heart of the system."""

    __tablename__ = "declarations"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    statut = db.Column(db.String(40), nullable=False, default=STATUT_EN_ATTENTE)
    priorite = db.Column(db.String(40), nullable=False, default=PRIORITE_MOYENNE)
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_resolution = db.Column(db.DateTime)

    # Rule 13: keep the historical author reference; do not delete declarations
    # when a user is removed (FK is nullable and not cascading).
    declarant_id = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False
    )
    technicien_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"))
    # Rule 6: a declaration must be linked to a category and a location.
    categorie_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False
    )
    emplacement_id = db.Column(
        db.Integer, db.ForeignKey("emplacements.id"), nullable=False
    )
    # Optional link to the faulty asset from the equipment park.
    equipement_id = db.Column(db.Integer, db.ForeignKey("equipements.id"))

    declarant = db.relationship("Utilisateur", foreign_keys=[declarant_id])
    technicien = db.relationship("Utilisateur", foreign_keys=[technicien_id])
    categorie = db.relationship("Categorie")
    emplacement = db.relationship("Emplacement")
    equipement = db.relationship("Equipement")

    commentaires = db.relationship(
        "Commentaire", back_populates="declaration", cascade="all, delete-orphan"
    )
    pieces_jointes = db.relationship(
        "PieceJointe", back_populates="declaration", cascade="all, delete-orphan"
    )
    historique = db.relationship(
        "HistoriqueStatut", back_populates="declaration", cascade="all, delete-orphan"
    )
    alertes = db.relationship(
        "Alerte", back_populates="declaration", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Declaration {self.id} {self.titre!r} [{self.statut}]>"


class Commentaire(db.Model):
    """A message in the discussion thread of an incident."""

    __tablename__ = "commentaires"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False
    )
    auteur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_publication = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Private notes between technicians, invisible to the requester.
    est_interne = db.Column(db.Boolean, nullable=False, default=False)

    declaration = db.relationship("Declaration", back_populates="commentaires")
    auteur = db.relationship("Utilisateur")

    def __repr__(self):
        return f"<Commentaire {self.id} decl={self.declaration_id}>"


class PieceJointe(db.Model):
    """An attachment (photo of the fault, screenshot, ...)."""

    __tablename__ = "pieces_jointes"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False
    )
    nom_fichier = db.Column(db.String(255), nullable=False)
    url_stockage = db.Column(db.String(512), nullable=False)
    date_telechargement = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    declaration = db.relationship("Declaration", back_populates="pieces_jointes")

    def __repr__(self):
        return f"<PieceJointe {self.nom_fichier}>"


class HistoriqueStatut(db.Model):
    """Status change history, used to measure processing time (SLA)."""

    __tablename__ = "historique_statuts"

    id = db.Column(db.Integer, primary_key=True)
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False
    )
    statut_precedent = db.Column(db.String(40))
    nouveau_statut = db.Column(db.String(40), nullable=False)
    modifie_par_user_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"))
    date_changement = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    declaration = db.relationship("Declaration", back_populates="historique")
    modifie_par = db.relationship("Utilisateur")

    def __repr__(self):
        return f"<HistoriqueStatut decl={self.declaration_id} {self.nouveau_statut}>"


class Alerte(db.Model):
    """A notification signalling activity on a declaration to a recipient.

    Created when a requester files a declaration or posts a message, so the
    relevant technician (or admin) is warned and can review it.
    """

    __tablename__ = "alertes"

    id = db.Column(db.Integer, primary_key=True)
    destinataire_id = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False
    )
    declaration_id = db.Column(
        db.Integer, db.ForeignKey("declarations.id"), nullable=False
    )
    type_alerte = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    lu = db.Column(db.Boolean, nullable=False, default=False)
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    destinataire = db.relationship("Utilisateur")
    declaration = db.relationship("Declaration", back_populates="alertes")

    def __repr__(self):
        return f"<Alerte {self.type_alerte} -> user={self.destinataire_id} lu={self.lu}>"
