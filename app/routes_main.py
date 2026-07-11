"""Main application routes: dashboard, declaration detail and actions."""

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from .auth_helpers import login_required
from .constants import PRIORITES
from .extensions import db
from .models import Alerte, Categorie, Declaration, Emplacement, Equipement
from .services import (
    ServiceError,
    ajouter_commentaire,
    alertes_pour,
    can_view_declaration,
    commentaires_visibles,
    create_declaration,
    declarations_visibles,
    marquer_alerte_lue,
    marquer_toutes_alertes_lues,
    prendre_en_charge,
    rejeter,
    resoudre,
)

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    declarations = declarations_visibles(g.user)
    return render_template("dashboard.html", declarations=declarations)


@bp.route("/declarations/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        try:
            declaration = create_declaration(
                declarant=g.user,
                titre=request.form.get("titre", ""),
                description=request.form.get("description", ""),
                categorie_id=request.form.get("categorie_id", type=int),
                emplacement_id=request.form.get("emplacement_id", type=int),
                priorite=request.form.get("priorite", ""),
                equipement_id=request.form.get("equipement_id", type=int),
            )
        except ServiceError as exc:
            flash(str(exc), "danger")
        else:
            flash("Déclaration créée.", "success")
            return redirect(url_for("main.detail", declaration_id=declaration.id))
    return render_template(
        "create.html",
        categories=Categorie.query.all(),
        emplacements=Emplacement.query.all(),
        equipements=Equipement.query.order_by(Equipement.nom).all(),
        priorites=PRIORITES,
    )


@bp.route("/declarations/<int:declaration_id>")
@login_required
def detail(declaration_id):
    declaration = db.session.get(Declaration, declaration_id) or abort(404)
    if not can_view_declaration(g.user, declaration):
        abort(403)
    return render_template(
        "detail.html",
        declaration=declaration,
        commentaires=commentaires_visibles(g.user, declaration),
    )


@bp.route("/declarations/<int:declaration_id>/comment", methods=["POST"])
@login_required
def comment(declaration_id):
    declaration = db.session.get(Declaration, declaration_id) or abort(404)
    if not can_view_declaration(g.user, declaration):
        abort(403)
    est_interne = request.form.get("est_interne") == "on"
    try:
        ajouter_commentaire(
            declaration, g.user, request.form.get("message", ""), est_interne
        )
    except ServiceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Commentaire ajouté.", "success")
    return redirect(url_for("main.detail", declaration_id=declaration_id))


@bp.route("/declarations/<int:declaration_id>/prendre", methods=["POST"])
@login_required
def prendre(declaration_id):
    declaration = db.session.get(Declaration, declaration_id) or abort(404)
    try:
        prendre_en_charge(declaration, g.user)
    except ServiceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Déclaration prise en charge.", "success")
    return redirect(url_for("main.detail", declaration_id=declaration_id))


@bp.route("/declarations/<int:declaration_id>/resoudre", methods=["POST"])
@login_required
def resoudre_view(declaration_id):
    declaration = db.session.get(Declaration, declaration_id) or abort(404)
    action = request.form.get("action", "resoudre")
    commentaire = request.form.get("commentaire_final", "")
    try:
        if action == "rejeter":
            rejeter(declaration, g.user, commentaire)
        else:
            resoudre(declaration, g.user, commentaire)
    except ServiceError as exc:
        flash(str(exc), "danger")
    else:
        flash("Déclaration clôturée.", "success")
    return redirect(url_for("main.detail", declaration_id=declaration_id))


@bp.route("/alertes")
@login_required
def alertes():
    return render_template("alertes.html", alertes=alertes_pour(g.user))


@bp.route("/alertes/lire", methods=["POST"])
@login_required
def alertes_tout_lire():
    marquer_toutes_alertes_lues(g.user)
    flash("Alertes marquées comme lues.", "success")
    return redirect(url_for("main.alertes"))


@bp.route("/alertes/<int:alerte_id>")
@login_required
def alerte_ouvrir(alerte_id):
    alerte = db.session.get(Alerte, alerte_id) or abort(404)
    try:
        marquer_alerte_lue(alerte, g.user)
    except ServiceError:
        abort(403)
    return redirect(url_for("main.detail", declaration_id=alerte.declaration_id))
