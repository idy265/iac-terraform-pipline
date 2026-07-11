"""Unit tests for the ORM models."""

from app.constants import PLATEFORME_INFORMATIQUE
from app.models import Categorie, Emplacement, Site, Utilisateur


def test_password_is_hashed_and_verifiable(fixtures):
    user = fixtures["demandeur"]
    assert user.password_hash != "password123"
    assert user.check_password("password123") is True
    assert user.check_password("wrong") is False


def test_role_properties(fixtures):
    assert fixtures["demandeur"].is_demandeur is True
    assert fixtures["demandeur"].is_technicien is False
    assert fixtures["tech_info"].is_technicien is True
    assert fixtures["admin"].is_admin is True


def test_site_deletion_cascades_to_emplacements(db, fixtures):
    # Rule 14: deleting a site removes its locations.
    site_id = fixtures["site"].id
    assert Emplacement.query.filter_by(site_id=site_id).count() == 1
    db.session.delete(fixtures["site"])
    db.session.commit()
    assert db.session.get(Site, site_id) is None
    assert Emplacement.query.filter_by(site_id=site_id).count() == 0


def test_category_self_reference(db, roles):
    parent = Categorie(nom="Informatique", type_plateforme=PLATEFORME_INFORMATIQUE)
    db.session.add(parent)
    db.session.flush()
    child = Categorie(
        nom="Réseau", type_plateforme=PLATEFORME_INFORMATIQUE, parent_id=parent.id
    )
    db.session.add(child)
    db.session.commit()
    assert child.parent is parent
    assert child in parent.sous_categories


def test_repr_does_not_crash(fixtures):
    assert "Utilisateur" in repr(fixtures["demandeur"])
    assert "Site" in repr(fixtures["site"])
