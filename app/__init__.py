"""Application factory for the incident / work-order management platform."""

import os

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .extensions import db


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enforce foreign-key constraints (incl. ON DELETE CASCADE) on SQLite."""
    module = type(dbapi_connection).__module__
    if "sqlite" in module:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///incidents.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if config:
        app.config.update(config)

    db.init_app(app)

    from . import models  # noqa: F401  (register models with SQLAlchemy)
    from .routes_auth import bp as auth_bp
    from .routes_main import bp as main_bp
    from .ui import register_ui_helpers

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    register_ui_helpers(app)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app):
    from flask import g, render_template

    _messages = {
        403: "Vous n'avez pas l'autorisation d'accéder à cette ressource.",
        404: "La page demandée est introuvable.",
    }

    def _handler(err):
        code = getattr(err, "code", 500)
        # Styled page only makes sense for logged-in users (needs dashboard link).
        if getattr(g, "user", None) is None:
            return err
        return (
            render_template(
                "error.html", code=code, message=_messages.get(code, "Une erreur est survenue.")
            ),
            code,
        )

    for _code in (403, 404):
        app.register_error_handler(_code, _handler)
