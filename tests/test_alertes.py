"""Unit tests for the alert / notification system."""

import pytest

from app.constants import (
    ALERTE_NOUVEAU_COMMENTAIRE,
    ALERTE_NOUVELLE_DECLARATION,
    PRIORITE_HAUTE,
)
from app.models import Alerte
from app.services import (
    PermissionError_,
    ajouter_commentaire,
    alertes_pour,
    compter_alertes_non_lues,
    create_declaration,
    marquer_alerte_lue,
    marquer_toutes_alertes_lues,
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


def test_new_declaration_alerts_matching_technician_and_admin(fixtures):
    _new_declaration(fixtures)

    tech_info_alerts = alertes_pour(fixtures["tech_info"])
    admin_alerts = alertes_pour(fixtures["admin"])
    assert len(tech_info_alerts) == 1
    assert tech_info_alerts[0].type_alerte == ALERTE_NOUVELLE_DECLARATION
    assert len(admin_alerts) == 1


def test_new_declaration_does_not_alert_other_specialty(fixtures):
    _new_declaration(fixtures)  # Informatique declaration
    # The building technician must not be notified for an IT incident.
    assert alertes_pour(fixtures["tech_bat"]) == []


def test_new_declaration_does_not_alert_the_declarant(fixtures):
    _new_declaration(fixtures)
    assert alertes_pour(fixtures["demandeur"]) == []


def test_new_alerts_are_unread(fixtures):
    _new_declaration(fixtures)
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 1


def test_requester_comment_alerts_technician(fixtures):
    decl = _new_declaration(fixtures)
    before = compter_alertes_non_lues(fixtures["tech_info"])
    ajouter_commentaire(decl, fixtures["demandeur"], "Toujours en panne ?")
    after = compter_alertes_non_lues(fixtures["tech_info"])
    assert after == before + 1
    assert alertes_pour(fixtures["tech_info"])[0].type_alerte == ALERTE_NOUVEAU_COMMENTAIRE


def test_public_technician_comment_alerts_requester(fixtures):
    decl = _new_declaration(fixtures)
    ajouter_commentaire(decl, fixtures["tech_info"], "Nous regardons cela.")
    assert compter_alertes_non_lues(fixtures["demandeur"]) == 1


def test_internal_note_does_not_alert_requester(fixtures):
    decl = _new_declaration(fixtures)
    ajouter_commentaire(
        decl, fixtures["tech_info"], "Note privée", est_interne=True
    )
    assert alertes_pour(fixtures["demandeur"]) == []
    # Admin (technician-side) is still notified of internal activity.
    assert compter_alertes_non_lues(fixtures["admin"]) >= 1


def test_author_is_never_alerted_for_own_comment(fixtures):
    decl = _new_declaration(fixtures)
    ajouter_commentaire(decl, fixtures["tech_info"], "Je prends en charge.")
    for a in alertes_pour(fixtures["tech_info"]):
        assert a.type_alerte != ALERTE_NOUVEAU_COMMENTAIRE


def test_mark_single_alert_read(db, fixtures):
    _new_declaration(fixtures)
    alerte = alertes_pour(fixtures["tech_info"])[0]
    marquer_alerte_lue(alerte, fixtures["tech_info"])
    assert alerte.lu is True
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 0


def test_mark_alert_read_wrong_recipient_forbidden(fixtures):
    _new_declaration(fixtures)
    alerte = alertes_pour(fixtures["tech_info"])[0]
    with pytest.raises(PermissionError_):
        marquer_alerte_lue(alerte, fixtures["tech_bat"])


def test_mark_all_alerts_read(db, fixtures):
    decl = _new_declaration(fixtures)
    ajouter_commentaire(decl, fixtures["demandeur"], "Merci de traiter.")
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 2
    n = marquer_toutes_alertes_lues(fixtures["tech_info"])
    assert n == 2
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 0


def test_alertes_pour_only_unread_filter(db, fixtures):
    decl = _new_declaration(fixtures)
    ajouter_commentaire(decl, fixtures["demandeur"], "Relance.")
    alerte = alertes_pour(fixtures["tech_info"])[0]
    marquer_alerte_lue(alerte, fixtures["tech_info"])
    assert len(alertes_pour(fixtures["tech_info"], seulement_non_lues=True)) == 1


def test_deleting_declaration_cascades_alerts(db, fixtures):
    decl = _new_declaration(fixtures)
    decl_id = decl.id
    assert Alerte.query.filter_by(declaration_id=decl_id).count() >= 1
    db.session.delete(decl)
    db.session.commit()
    assert Alerte.query.filter_by(declaration_id=decl_id).count() == 0


def test_anonymous_user_has_no_alerts():
    assert compter_alertes_non_lues(None) == 0
    assert alertes_pour(None) == []
    assert marquer_toutes_alertes_lues(None) == 0
