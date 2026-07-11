"""Session helpers and access decorators for the web layer."""

from functools import wraps

from flask import flash, g, redirect, session, url_for

from .extensions import db
from .models import Utilisateur


def load_current_user():
    """Load the logged-in user into ``flask.g`` (called before each request)."""
    user_id = session.get("user_id")
    g.user = db.session.get(Utilisateur, user_id) if user_id else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "user", None) is None:
            flash("Veuillez vous connecter.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
