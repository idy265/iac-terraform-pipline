"""Business-rule service layer.

All the access-control and lifecycle rules (Rules 1-14 of the specification)
live here so they can be reused by the web routes and covered by unit tests
independently of the HTTP layer.
"""

from datetime import datetime

from .constants import (
    ROLE_ADMIN,
    STATUT_EN_ATTENTE,
    STATUT_EN_COURS,
    STATUT_REJETE,
    STATUT_RESOLU,
    STATUTS_TERMINES,
)
from .extensions import db
from .models import (
    Categorie,
    Commentaire,
    Declaration,
    Emplacement,
    HistoriqueStatut,
    PieceJointe,
    Utilisateur,
)


class ServiceError(Exception):
    """Base class for business-rule violations."""


class PermissionError_(ServiceError):
    """Raised when a user is not allowed to perform an action."""


class ValidationError(ServiceError):
    """Raised when input data does not satisfy the business rules."""


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def authenticate(email, password):
    """Return the matching user for valid credentials, else ``None``."""
    if not email or not password:
        return None
    user = Utilisateur.query.filter_by(email=email).first()
    if user is not None and user.check_password(password):
        return user
    return None


# ---------------------------------------------------------------------------
# Access control (Rules 1-4)
# ---------------------------------------------------------------------------
def can_view_declaration(user, declaration):
    """Whether ``user`` may view ``declaration``.

    Rule 1: a requester can see their own declarations.
    Rule 2: a requester cannot see other users' declarations.
    Rule 3: a technician only sees declarations matching their specialty.
    Rule 4: the administrator can see everything.
    """
    if user is None or declaration is None:
        return False
    if user.is_admin:
        return True
    if user.is_technicien:
        categorie = declaration.categorie
        return categorie is not None and categorie.type_plateforme == user.specialite
    # Demandeur (or any other role): only their own declarations.
    return declaration.declarant_id == user.id


def declarations_visibles(user):
    """Return the list of declarations ``user`` is allowed to see."""
    if user is None:
        return []
    query = Declaration.query
    if user.is_admin:
        return query.order_by(Declaration.date_creation.desc()).all()
    if user.is_technicien:
        return (
            query.join(Categorie, Declaration.categorie_id == Categorie.id)
            .filter(Categorie.type_plateforme == user.specialite)
            .order_by(Declaration.date_creation.desc())
            .all()
        )
    return (
        query.filter(Declaration.declarant_id == user.id)
        .order_by(Declaration.date_creation.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Declaration lifecycle
# ---------------------------------------------------------------------------
def create_declaration(
    declarant,
    titre,
    description,
    categorie_id,
    emplacement_id,
    priorite,
    commit=True,
):
    """Create a new declaration.

    Rule 5: the status is always "En attente" at creation.
    Rule 6: a declaration must be linked to a site, a precise location and a
    category (the location carries the site).
    """
    if declarant is None:
        raise PermissionError_("Un utilisateur authentifié est requis.")
    if not titre or not titre.strip():
        raise ValidationError("Le titre est obligatoire.")

    categorie = db.session.get(Categorie, categorie_id)
    if categorie is None:
        raise ValidationError("La catégorie est obligatoire et doit exister.")

    emplacement = db.session.get(Emplacement, emplacement_id)
    if emplacement is None:
        raise ValidationError("L'emplacement est obligatoire et doit exister.")

    declaration = Declaration(
        titre=titre.strip(),
        description=description,
        statut=STATUT_EN_ATTENTE,  # Rule 5
        priorite=priorite,
        declarant_id=declarant.id,
        categorie_id=categorie.id,
        emplacement_id=emplacement.id,
    )
    db.session.add(declaration)
    db.session.flush()
    _record_history(declaration, None, STATUT_EN_ATTENTE, declarant)
    if commit:
        db.session.commit()
    return declaration


def prendre_en_charge(declaration, technicien, commit=True):
    """A technician takes charge of a declaration.

    Rule 7: the status becomes "En cours" and ``technicien_id`` is filled in.
    Rule 3: a technician may only take charge of declarations of their specialty.
    """
    if technicien is None or not (technicien.is_technicien or technicien.is_admin):
        raise PermissionError_("Seul un technicien ou un administrateur peut prendre en charge.")
    if not can_view_declaration(technicien, declaration):
        raise PermissionError_("Cette déclaration ne correspond pas à votre spécialité.")
    if declaration.statut in STATUTS_TERMINES:
        raise ValidationError("Cette déclaration est déjà clôturée.")

    ancien = declaration.statut
    declaration.technicien_id = technicien.id  # Rule 7
    declaration.statut = STATUT_EN_COURS  # Rule 7
    _record_history(declaration, ancien, STATUT_EN_COURS, technicien)
    if commit:
        db.session.commit()
    return declaration


def _cloturer(declaration, intervenant, nouveau_statut, commentaire_final, commit):
    """Shared logic for resolving/rejecting a declaration (Rules 8, 9)."""
    if intervenant is None or not (intervenant.is_technicien or intervenant.is_admin):
        raise PermissionError_("Seul un technicien ou un administrateur peut clôturer.")
    if not can_view_declaration(intervenant, declaration):
        raise PermissionError_("Cette déclaration ne correspond pas à votre spécialité.")
    # Rule 8: a final comment is required.
    if not commentaire_final or not commentaire_final.strip():
        raise ValidationError(
            "Un commentaire final est obligatoire pour résoudre ou rejeter."
        )

    ancien = declaration.statut
    ajouter_commentaire(
        declaration, intervenant, commentaire_final, est_interne=False, commit=False
    )
    declaration.statut = nouveau_statut
    declaration.date_resolution = datetime.utcnow()  # Rule 9
    _record_history(declaration, ancien, nouveau_statut, intervenant)
    if commit:
        db.session.commit()
    return declaration


def resoudre(declaration, intervenant, commentaire_final, commit=True):
    """Mark a declaration as resolved (Rules 8, 9)."""
    return _cloturer(declaration, intervenant, STATUT_RESOLU, commentaire_final, commit)


def rejeter(declaration, intervenant, commentaire_final, commit=True):
    """Reject a declaration (Rules 8, 9)."""
    return _cloturer(declaration, intervenant, STATUT_REJETE, commentaire_final, commit)


# ---------------------------------------------------------------------------
# Comments and attachments (Rules 10, 11, 12)
# ---------------------------------------------------------------------------
def ajouter_commentaire(declaration, auteur, message, est_interne=False, commit=True):
    """Add a comment to a declaration.

    Rule 12: no new comment can be added once the declaration is finished.
    Internal comments are only allowed for technicians/admins.
    """
    if auteur is None:
        raise PermissionError_("Un utilisateur authentifié est requis.")
    if not message or not message.strip():
        raise ValidationError("Le message ne peut pas être vide.")
    if declaration.statut in STATUTS_TERMINES and commit:
        # ``commit=False`` is used internally when closing a ticket, which is
        # the one legitimate case of writing while the ticket transitions.
        raise ValidationError(
            "Impossible d'ajouter un commentaire à une déclaration clôturée."
        )
    if est_interne and not (auteur.is_technicien or auteur.is_admin):
        raise PermissionError_("Seuls les techniciens peuvent écrire des notes internes.")

    commentaire = Commentaire(
        declaration_id=declaration.id,
        auteur_id=auteur.id,
        message=message.strip(),
        est_interne=est_interne,
    )
    db.session.add(commentaire)
    if commit:
        db.session.commit()
    return commentaire


def commentaires_visibles(user, declaration):
    """Return comments visible to ``user`` (internal notes hidden from requesters)."""
    visibles = []
    for c in declaration.commentaires:
        if c.est_interne and not (user.is_technicien or user.is_admin):
            continue
        visibles.append(c)
    return visibles


def modifier_commentaire(commentaire, user, nouveau_message, commit=True):
    """Edit a comment.

    Rule 10: only the author or an administrator may edit/delete a comment.
    """
    if not _peut_modifier_commentaire(commentaire, user):
        raise PermissionError_("Seul l'auteur ou un administrateur peut modifier ce commentaire.")
    if not nouveau_message or not nouveau_message.strip():
        raise ValidationError("Le message ne peut pas être vide.")
    commentaire.message = nouveau_message.strip()
    if commit:
        db.session.commit()
    return commentaire


def supprimer_commentaire(commentaire, user, commit=True):
    """Delete a comment (Rule 10)."""
    if not _peut_modifier_commentaire(commentaire, user):
        raise PermissionError_("Seul l'auteur ou un administrateur peut supprimer ce commentaire.")
    db.session.delete(commentaire)
    if commit:
        db.session.commit()


def _peut_modifier_commentaire(commentaire, user):
    if user is None:
        return False
    return user.is_admin or commentaire.auteur_id == user.id


def ajouter_piece_jointe(declaration, user, nom_fichier, url_stockage, commit=True):
    """Attach a file to a declaration.

    Rule 11: attachments are optional at creation.
    Rule 12: no new attachment once the declaration is finished.
    """
    if user is None:
        raise PermissionError_("Un utilisateur authentifié est requis.")
    if not nom_fichier or not url_stockage:
        raise ValidationError("Le fichier et son emplacement sont obligatoires.")
    if declaration.statut in STATUTS_TERMINES:
        raise ValidationError(
            "Impossible d'ajouter une pièce jointe à une déclaration clôturée."
        )
    piece = PieceJointe(
        declaration_id=declaration.id,
        nom_fichier=nom_fichier,
        url_stockage=url_stockage,
    )
    db.session.add(piece)
    if commit:
        db.session.commit()
    return piece


# ---------------------------------------------------------------------------
# Users (Rule 13)
# ---------------------------------------------------------------------------
def anonymiser_utilisateur(user, commit=True):
    """Anonymise a user instead of deleting them.

    Rule 13: deleting a user must not delete their past declarations; the name
    is frozen/anonymised so the incident history is preserved.
    """
    if user is None:
        raise ValidationError("Utilisateur introuvable.")
    user.nom = "Utilisateur anonymisé"
    user.prenom = None
    user.telephone = None
    user.email = f"anonyme+{user.id}@example.invalid"
    if commit:
        db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _record_history(declaration, ancien_statut, nouveau_statut, user):
    db.session.add(
        HistoriqueStatut(
            declaration_id=declaration.id,
            statut_precedent=ancien_statut,
            nouveau_statut=nouveau_statut,
            modifie_par_user_id=user.id if user is not None else None,
        )
    )


def is_admin_role_name(name):
    return name == ROLE_ADMIN
