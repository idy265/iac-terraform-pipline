"""Unit tests for the business-rule service layer (Rules 1-14)."""

import pytest

from app.constants import (
    PRIORITE_HAUTE,
    STATUT_CLOTURE,
    STATUT_EN_ATTENTE,
    STATUT_EN_COURS,
    STATUT_REJETE,
    STATUT_RESOLU,
)
from app.models import Commentaire, Declaration, HistoriqueStatut
from app.services import (
    PermissionError_,
    ValidationError,
    ajouter_commentaire,
    ajouter_piece_jointe,
    anonymiser_utilisateur,
    authenticate,
    can_view_declaration,
    commentaires_visibles,
    create_declaration,
    declarations_visibles,
    modifier_commentaire,
    prendre_en_charge,
    rejeter,
    resoudre,
    supprimer_commentaire,
)


def _new_declaration(fixtures, declarant=None, categorie=None):
    return create_declaration(
        declarant=declarant or fixtures["demandeur"],
        titre="PC en panne",
        description="Ne démarre pas",
        categorie_id=(categorie or fixtures["cat_info"]).id,
        emplacement_id=fixtures["emplacement"].id,
        priorite=PRIORITE_HAUTE,
    )


# --- Authentication --------------------------------------------------------
def test_authenticate_valid(fixtures):
    user = authenticate("jean@example.com", "password123")
    assert user is not None and user.id == fixtures["demandeur"].id


@pytest.mark.parametrize(
    "email,password",
    [
        ("jean@example.com", "wrong"),
        ("unknown@example.com", "password123"),
        ("", ""),
        ("jean@example.com", ""),
    ],
)
def test_authenticate_invalid(fixtures, email, password):
    assert authenticate(email, password) is None


# --- Creation (Rules 5, 6) -------------------------------------------------
def test_create_declaration_defaults_to_en_attente(fixtures):
    decl = _new_declaration(fixtures)
    assert decl.statut == STATUT_EN_ATTENTE  # Rule 5
    assert decl.declarant_id == fixtures["demandeur"].id


def test_create_declaration_records_history(db, fixtures):
    decl = _new_declaration(fixtures)
    hist = HistoriqueStatut.query.filter_by(declaration_id=decl.id).all()
    assert len(hist) == 1
    assert hist[0].nouveau_statut == STATUT_EN_ATTENTE


def test_create_declaration_requires_title(fixtures):
    with pytest.raises(ValidationError):
        create_declaration(
            declarant=fixtures["demandeur"],
            titre="   ",
            description="x",
            categorie_id=fixtures["cat_info"].id,
            emplacement_id=fixtures["emplacement"].id,
            priorite=PRIORITE_HAUTE,
        )


def test_create_declaration_requires_valid_category(fixtures):
    with pytest.raises(ValidationError):
        create_declaration(
            declarant=fixtures["demandeur"],
            titre="x",
            description="x",
            categorie_id=9999,
            emplacement_id=fixtures["emplacement"].id,
            priorite=PRIORITE_HAUTE,
        )


def test_create_declaration_requires_valid_location(fixtures):
    with pytest.raises(ValidationError):
        create_declaration(
            declarant=fixtures["demandeur"],
            titre="x",
            description="x",
            categorie_id=fixtures["cat_info"].id,
            emplacement_id=9999,
            priorite=PRIORITE_HAUTE,
        )


def test_create_declaration_requires_authenticated_user(fixtures):
    with pytest.raises(PermissionError_):
        create_declaration(
            declarant=None,
            titre="x",
            description="x",
            categorie_id=fixtures["cat_info"].id,
            emplacement_id=fixtures["emplacement"].id,
            priorite=PRIORITE_HAUTE,
        )


# --- Access control (Rules 1-4) -------------------------------------------
def test_requester_sees_only_own_declaration(fixtures):
    decl = _new_declaration(fixtures, declarant=fixtures["demandeur"])
    assert can_view_declaration(fixtures["demandeur"], decl) is True  # Rule 1
    assert can_view_declaration(fixtures["autre_demandeur"], decl) is False  # Rule 2


def test_technician_sees_only_matching_specialty(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    assert can_view_declaration(fixtures["tech_info"], decl) is True  # Rule 3
    assert can_view_declaration(fixtures["tech_bat"], decl) is False  # Rule 3


def test_admin_sees_everything(fixtures):
    decl = _new_declaration(fixtures)
    assert can_view_declaration(fixtures["admin"], decl) is True  # Rule 4


def test_can_view_none(fixtures):
    assert can_view_declaration(None, None) is False


def test_declarations_visibles_per_role(fixtures):
    d_info = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    d_bat = _new_declaration(fixtures, categorie=fixtures["cat_bat"])
    d_other = _new_declaration(fixtures, declarant=fixtures["autre_demandeur"])

    demandeur_ids = {d.id for d in declarations_visibles(fixtures["demandeur"])}
    assert d_info.id in demandeur_ids and d_bat.id in demandeur_ids
    assert d_other.id not in demandeur_ids

    tech_info_ids = {d.id for d in declarations_visibles(fixtures["tech_info"])}
    assert d_info.id in tech_info_ids
    assert d_bat.id not in tech_info_ids

    admin_ids = {d.id for d in declarations_visibles(fixtures["admin"])}
    assert {d_info.id, d_bat.id, d_other.id} <= admin_ids

    assert declarations_visibles(None) == []


# --- Lifecycle: prise en charge (Rules 3, 7) ------------------------------
def test_prendre_en_charge_sets_status_and_technician(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    prendre_en_charge(decl, fixtures["tech_info"])
    assert decl.statut == STATUT_EN_COURS  # Rule 7
    assert decl.technicien_id == fixtures["tech_info"].id  # Rule 7


def test_prendre_en_charge_wrong_specialty_denied(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    with pytest.raises(PermissionError_):
        prendre_en_charge(decl, fixtures["tech_bat"])  # Rule 3


def test_prendre_en_charge_requires_technician(fixtures):
    decl = _new_declaration(fixtures)
    with pytest.raises(PermissionError_):
        prendre_en_charge(decl, fixtures["demandeur"])


# --- Lifecycle: résolution / rejet (Rules 8, 9) ---------------------------
def test_resoudre_requires_final_comment(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    with pytest.raises(ValidationError):
        resoudre(decl, fixtures["tech_info"], "")  # Rule 8


def test_resoudre_sets_resolution_date_and_comment(db, fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    resoudre(decl, fixtures["tech_info"], "Remplacement de l'alimentation")
    assert decl.statut == STATUT_RESOLU
    assert decl.date_resolution is not None  # Rule 9
    comments = Commentaire.query.filter_by(declaration_id=decl.id).all()
    assert any("alimentation" in c.message for c in comments)  # Rule 8


def test_rejeter_sets_status_and_date(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    rejeter(decl, fixtures["tech_info"], "Hors périmètre")
    assert decl.statut == STATUT_REJETE
    assert decl.date_resolution is not None  # Rule 9


def test_admin_can_resolve(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_bat"])
    resoudre(decl, fixtures["admin"], "Traité par l'admin")
    assert decl.statut == STATUT_RESOLU


# --- Comments (Rules 10, 12) & internal notes ------------------------------
def test_add_comment(fixtures):
    decl = _new_declaration(fixtures)
    c = ajouter_commentaire(decl, fixtures["demandeur"], "Bonjour")
    assert c.id is not None and c.est_interne is False


def test_add_empty_comment_rejected(fixtures):
    decl = _new_declaration(fixtures)
    with pytest.raises(ValidationError):
        ajouter_commentaire(decl, fixtures["demandeur"], "   ")


def test_cannot_comment_closed_declaration(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    resoudre(decl, fixtures["tech_info"], "Réparé")
    with pytest.raises(ValidationError):  # Rule 12
        ajouter_commentaire(decl, fixtures["demandeur"], "Merci")


def test_internal_note_requires_technician(fixtures):
    decl = _new_declaration(fixtures)
    with pytest.raises(PermissionError_):
        ajouter_commentaire(
            decl, fixtures["demandeur"], "note", est_interne=True
        )


def test_internal_notes_hidden_from_requester(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    ajouter_commentaire(decl, fixtures["demandeur"], "public")
    ajouter_commentaire(
        decl, fixtures["tech_info"], "note privée", est_interne=True
    )
    vus_demandeur = commentaires_visibles(fixtures["demandeur"], decl)
    vus_tech = commentaires_visibles(fixtures["tech_info"], decl)
    assert len(vus_demandeur) == 1
    assert len(vus_tech) == 2


def test_only_author_or_admin_can_edit_comment(fixtures):
    decl = _new_declaration(fixtures)
    c = ajouter_commentaire(decl, fixtures["demandeur"], "original")
    with pytest.raises(PermissionError_):  # Rule 10
        modifier_commentaire(c, fixtures["autre_demandeur"], "hack")
    modifier_commentaire(c, fixtures["demandeur"], "corrigé")
    assert c.message == "corrigé"


def test_admin_can_delete_any_comment(db, fixtures):
    decl = _new_declaration(fixtures)
    c = ajouter_commentaire(decl, fixtures["demandeur"], "à supprimer")
    supprimer_commentaire(c, fixtures["admin"])  # Rule 10
    assert db.session.get(Commentaire, c.id) is None


# --- Attachments (Rules 11, 12) -------------------------------------------
def test_add_attachment(fixtures):
    decl = _new_declaration(fixtures)
    p = ajouter_piece_jointe(decl, fixtures["demandeur"], "photo.jpg", "/files/photo.jpg")
    assert p.id is not None


def test_cannot_attach_to_closed_declaration(fixtures):
    decl = _new_declaration(fixtures, categorie=fixtures["cat_info"])
    resoudre(decl, fixtures["tech_info"], "Réparé")
    with pytest.raises(ValidationError):  # Rule 12
        ajouter_piece_jointe(decl, fixtures["demandeur"], "x.jpg", "/x.jpg")


# --- User anonymisation (Rule 13) -----------------------------------------
def test_anonymiser_utilisateur_keeps_declarations(db, fixtures):
    decl = _new_declaration(fixtures, declarant=fixtures["demandeur"])
    user_id = fixtures["demandeur"].id
    anonymiser_utilisateur(fixtures["demandeur"])  # Rule 13
    kept = db.session.get(Declaration, decl.id)
    assert kept is not None and kept.declarant_id == user_id
    assert "anonym" in fixtures["demandeur"].nom.lower()
