"""Unit tests for the equipment park (equipements) and its links."""

import pytest

from app.constants import (
    EQUIP_EN_PANNE,
    EQUIP_FONCTIONNEL,
    PRIORITE_HAUTE,
)
from app.models import Emplacement, Equipement
from app.services import ValidationError, create_declaration


def _equipement(fixtures, statut=EQUIP_FONCTIONNEL):
    eq = Equipement(
        nom="PC bureau 302",
        code_barre="PC-000302",
        numero_serie="SN-1",
        type_equipement="PC Portable",
        emplacement_id=fixtures["emplacement"].id,
        statut=statut,
    )
    fixtures["cat_info"]  # touch to ensure fixtures loaded
    from app.extensions import db

    db.session.add(eq)
    db.session.commit()
    return eq


def test_equipement_defaults_to_fonctionnel(db, fixtures):
    eq = Equipement(nom="Imprimante", emplacement_id=fixtures["emplacement"].id)
    db.session.add(eq)
    db.session.commit()
    assert eq.statut == EQUIP_FONCTIONNEL


def test_equipement_repr(db, fixtures):
    eq = _equipement(fixtures, statut=EQUIP_EN_PANNE)
    assert "PC bureau 302" in repr(eq)
    assert EQUIP_EN_PANNE in repr(eq)


def test_create_declaration_links_equipement(db, fixtures):
    eq = _equipement(fixtures)
    decl = create_declaration(
        declarant=fixtures["demandeur"],
        titre="PC HS",
        description="",
        categorie_id=fixtures["cat_info"].id,
        emplacement_id=fixtures["emplacement"].id,
        priorite=PRIORITE_HAUTE,
        equipement_id=eq.id,
    )
    assert decl.equipement_id == eq.id
    assert decl.equipement.nom == "PC bureau 302"


def test_create_declaration_without_equipement(db, fixtures):
    decl = create_declaration(
        declarant=fixtures["demandeur"],
        titre="Souci réseau",
        description="",
        categorie_id=fixtures["cat_info"].id,
        emplacement_id=fixtures["emplacement"].id,
        priorite=PRIORITE_HAUTE,
    )
    assert decl.equipement_id is None


def test_create_declaration_invalid_equipement_rejected(db, fixtures):
    with pytest.raises(ValidationError):
        create_declaration(
            declarant=fixtures["demandeur"],
            titre="PC HS",
            description="",
            categorie_id=fixtures["cat_info"].id,
            emplacement_id=fixtures["emplacement"].id,
            priorite=PRIORITE_HAUTE,
            equipement_id=99999,
        )


def test_deleting_emplacement_cascades_to_equipements(db, fixtures):
    eq = _equipement(fixtures)
    eq_id = eq.id
    empl = db.session.get(Emplacement, fixtures["emplacement"].id)
    db.session.delete(empl)
    db.session.commit()
    assert db.session.get(Equipement, eq_id) is None
