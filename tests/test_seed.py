"""Tests for the demo-data seeding helpers."""

from app.constants import STATUT_EN_ATTENTE
from app.models import Declaration, Role, Utilisateur
from app.seed import seed_demo_data, seed_roles


def test_seed_roles_is_idempotent(db):
    seed_roles()
    seed_roles()
    assert Role.query.count() == 3


def test_seed_demo_data_populates_and_is_idempotent(db):
    seed_demo_data()
    users = Utilisateur.query.count()
    decls = Declaration.query.count()
    assert users == 3
    assert decls == 1

    # A demo user can authenticate and the demo ticket starts "En attente".
    jean = Utilisateur.query.filter_by(email="jean@example.com").first()
    assert jean is not None and jean.check_password("password123")
    assert Declaration.query.first().statut == STATUT_EN_ATTENTE

    # Running again must not duplicate data.
    seed_demo_data()
    assert Utilisateur.query.count() == users
    assert Declaration.query.count() == decls
