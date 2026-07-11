"""Seed helpers to populate the database with demo data."""

from .constants import (
    PLATEFORME_BATIMENT,
    PLATEFORME_INFORMATIQUE,
    PRIORITE_HAUTE,
    ROLE_ADMIN,
    ROLE_DEMANDEUR,
    ROLE_TECHNICIEN,
)
from .extensions import db
from .models import Categorie, Emplacement, Role, Site, Utilisateur
from .services import create_declaration


def seed_roles():
    """Create the default roles if they do not already exist."""
    roles = {}
    for nom in (ROLE_DEMANDEUR, ROLE_TECHNICIEN, ROLE_ADMIN):
        role = Role.query.filter_by(nom=nom).first()
        if role is None:
            role = Role(nom=nom)
            db.session.add(role)
        roles[nom] = role
    db.session.flush()
    return roles


def seed_demo_data():
    """Populate the database with a small, coherent demo dataset."""
    if Utilisateur.query.first() is not None:
        return  # already seeded

    roles = seed_roles()

    site = Site(nom="Siège Social", adresse="1 rue de l'Exemple")
    db.session.add(site)
    db.session.flush()

    emplacement = Emplacement(site_id=site.id, zone="Bureau 302")
    salle_serveurs = Emplacement(site_id=site.id, zone="Salle des serveurs")
    db.session.add_all([emplacement, salle_serveurs])

    cat_info = Categorie(nom="Réseau", type_plateforme=PLATEFORME_INFORMATIQUE)
    cat_bat = Categorie(nom="Plomberie", type_plateforme=PLATEFORME_BATIMENT)
    db.session.add_all([cat_info, cat_bat])

    demandeur = Utilisateur(
        nom="Dupont", prenom="Jean", email="jean@example.com", role=roles[ROLE_DEMANDEUR]
    )
    demandeur.set_password("password123")
    tech_info = Utilisateur(
        nom="Martin",
        prenom="Alice",
        email="alice@example.com",
        role=roles[ROLE_TECHNICIEN],
        specialite=PLATEFORME_INFORMATIQUE,
    )
    tech_info.set_password("password123")
    admin = Utilisateur(
        nom="Admin", prenom="Super", email="admin@example.com", role=roles[ROLE_ADMIN]
    )
    admin.set_password("password123")
    db.session.add_all([demandeur, tech_info, admin])
    db.session.flush()

    create_declaration(
        declarant=demandeur,
        titre="PC ne s'allume plus",
        description="Le poste du bureau 302 ne démarre plus.",
        categorie_id=cat_info.id,
        emplacement_id=emplacement.id,
        priorite=PRIORITE_HAUTE,
        commit=False,
    )
    db.session.commit()
