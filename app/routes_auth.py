"""Authentication routes."""

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth_helpers import load_current_user
from .services import authenticate

bp = Blueprint("auth", __name__)


@bp.before_app_request
def _before():
    load_current_user()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        user = authenticate(email, password)
        if user is None:
            flash("Identifiants invalides.", "danger")
        else:
            session.clear()
            session["user_id"] = user.id
            flash("Connexion réussie.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("auth.login"))
