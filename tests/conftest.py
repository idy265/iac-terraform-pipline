"""Shared pytest fixtures."""

import pytest

from app import create_app
from app.constants import (
    PLATEFORME_BATIMENT,
    PLATEFORME_INFORMATIQUE,
)
from app.extensions import db as _db
from app.models import Categorie, Emplacement, Site, Utilisateur
from app.seed import seed_roles


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test",
        }
    )
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def roles(db):
    return seed_roles()


@pytest.fixture
def fixtures(db, roles):
    """A coherent set of base objects reused across tests."""
    site = Site(nom="Siège", adresse="1 rue X")
    db.session.add(site)
    db.session.flush()

    empl = Emplacement(site_id=site.id, zone="Bureau 302")
    db.session.add(empl)

    cat_info = Categorie(nom="Réseau", type_plateforme=PLATEFORME_INFORMATIQUE)
    cat_bat = Categorie(nom="Plomberie", type_plateforme=PLATEFORME_BATIMENT)
    db.session.add_all([cat_info, cat_bat])

    demandeur = Utilisateur(
        nom="Dupont", prenom="Jean", email="jean@example.com", role=roles["Demandeur"]
    )
    demandeur.set_password("password123")
    autre_demandeur = Utilisateur(
        nom="Durand", prenom="Paul", email="paul@example.com", role=roles["Demandeur"]
    )
    autre_demandeur.set_password("password123")
    tech_info = Utilisateur(
        nom="Martin",
        prenom="Alice",
        email="alice@example.com",
        role=roles["Technicien"],
        specialite=PLATEFORME_INFORMATIQUE,
    )
    tech_info.set_password("password123")
    tech_bat = Utilisateur(
        nom="Bernard",
        prenom="Bob",
        email="bob@example.com",
        role=roles["Technicien"],
        specialite=PLATEFORME_BATIMENT,
    )
    tech_bat.set_password("password123")
    admin = Utilisateur(
        nom="Admin", prenom="Super", email="admin@example.com", role=roles["Admin"]
    )
    admin.set_password("password123")

    db.session.add_all([demandeur, autre_demandeur, tech_info, tech_bat, admin])
    db.session.commit()

    return {
        "site": site,
        "emplacement": empl,
        "cat_info": cat_info,
        "cat_bat": cat_bat,
        "demandeur": demandeur,
        "autre_demandeur": autre_demandeur,
        "tech_info": tech_info,
        "tech_bat": tech_bat,
        "admin": admin,
    }
