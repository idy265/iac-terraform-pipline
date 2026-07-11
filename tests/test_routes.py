"""Integration tests for the web routes."""

from app.constants import PRIORITE_HAUTE
from app.services import create_declaration


def _login(client, email, password="password123"):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


def _make_decl(fixtures, declarant_key="demandeur", categorie_key="cat_info"):
    return create_declaration(
        declarant=fixtures[declarant_key],
        titre="Panne",
        description="desc",
        categorie_id=fixtures[categorie_key].id,
        emplacement_id=fixtures["emplacement"].id,
        priorite=PRIORITE_HAUTE,
    )


def test_login_required_redirects(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_success_and_dashboard(client, fixtures):
    resp = _login(client, "jean@example.com")
    assert resp.status_code == 200
    assert "Tableau de bord".encode() in resp.data


def test_login_failure(client, fixtures):
    resp = _login(client, "jean@example.com", "wrong")
    assert "invalides".encode() in resp.data


def test_logout(client, fixtures):
    _login(client, "jean@example.com")
    resp = client.get("/logout", follow_redirects=True)
    assert "Connexion".encode() in resp.data


def test_create_declaration_via_form(client, fixtures):
    _login(client, "jean@example.com")
    resp = client.post(
        "/declarations/new",
        data={
            "titre": "Imprimante HS",
            "description": "plus d'encre",
            "categorie_id": fixtures["cat_info"].id,
            "emplacement_id": fixtures["emplacement"].id,
            "priorite": PRIORITE_HAUTE,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Imprimante HS".encode() in resp.data


def test_detail_forbidden_for_other_requester(client, fixtures):
    decl = _make_decl(fixtures, declarant_key="demandeur")
    _login(client, "paul@example.com")  # autre_demandeur
    resp = client.get(f"/declarations/{decl.id}")
    assert resp.status_code == 403


def test_detail_not_found(client, fixtures):
    _login(client, "admin@example.com")
    assert client.get("/declarations/9999").status_code == 404


def test_technicien_prend_en_charge_via_route(client, fixtures):
    decl = _make_decl(fixtures, categorie_key="cat_info")
    _login(client, "alice@example.com")  # tech_info
    resp = client.post(
        f"/declarations/{decl.id}/prendre", follow_redirects=True
    )
    assert resp.status_code == 200
    assert "En cours".encode() in resp.data


def test_resoudre_route_requires_comment(client, fixtures):
    decl = _make_decl(fixtures, categorie_key="cat_info")
    _login(client, "alice@example.com")
    resp = client.post(
        f"/declarations/{decl.id}/resoudre",
        data={"action": "resoudre", "commentaire_final": ""},
        follow_redirects=True,
    )
    assert "obligatoire".encode() in resp.data


def test_comment_route(client, fixtures):
    decl = _make_decl(fixtures, categorie_key="cat_info")
    _login(client, "jean@example.com")
    resp = client.post(
        f"/declarations/{decl.id}/comment",
        data={"message": "Un souci de plus"},
        follow_redirects=True,
    )
    assert "Un souci de plus".encode() in resp.data


def test_alertes_page_lists_new_declaration(client, fixtures):
    _make_decl(fixtures, declarant_key="demandeur", categorie_key="cat_info")
    _login(client, "alice@example.com")  # tech_info gets an alert
    resp = client.get("/alertes")
    assert resp.status_code == 200
    assert "Nouvelle déclaration".encode() in resp.data


def test_alerte_ouvrir_redirects_to_declaration_and_marks_read(client, fixtures):
    from app.services import alertes_pour, compter_alertes_non_lues

    decl = _make_decl(fixtures, categorie_key="cat_info")
    alerte = alertes_pour(fixtures["tech_info"])[0]
    _login(client, "alice@example.com")
    resp = client.get(f"/alertes/{alerte.id}", follow_redirects=False)
    assert resp.status_code == 302
    assert f"/declarations/{decl.id}" in resp.headers["Location"]
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 0


def test_alerte_ouvrir_forbidden_for_other_user(client, fixtures):
    from app.services import alertes_pour

    _make_decl(fixtures, categorie_key="cat_info")
    alerte = alertes_pour(fixtures["tech_info"])[0]
    _login(client, "bob@example.com")  # tech_bat, not the recipient
    assert client.get(f"/alertes/{alerte.id}").status_code == 403


def test_alertes_tout_lire_route(client, fixtures):
    from app.services import compter_alertes_non_lues

    _make_decl(fixtures, categorie_key="cat_info")
    _login(client, "alice@example.com")
    resp = client.post("/alertes/lire", follow_redirects=True)
    assert resp.status_code == 200
    assert compter_alertes_non_lues(fixtures["tech_info"]) == 0


def test_create_declaration_with_equipement_via_form(client, fixtures):
    from app.extensions import db
    from app.models import Equipement

    eq = Equipement(nom="Serveur A", emplacement_id=fixtures["emplacement"].id)
    db.session.add(eq)
    db.session.commit()
    _login(client, "jean@example.com")
    resp = client.post(
        "/declarations/new",
        data={
            "titre": "Serveur down",
            "description": "",
            "categorie_id": fixtures["cat_info"].id,
            "emplacement_id": fixtures["emplacement"].id,
            "priorite": PRIORITE_HAUTE,
            "equipement_id": eq.id,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Serveur A".encode() in resp.data
