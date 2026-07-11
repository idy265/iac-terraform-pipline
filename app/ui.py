"""UI helpers exposed to Jinja templates (status/priority styling, icons)."""

from .constants import (
    PRIORITE_BASSE,
    PRIORITE_CRITIQUE,
    PRIORITE_HAUTE,
    PRIORITE_MOYENNE,
    STATUT_CLOTURE,
    STATUT_EN_ATTENTE,
    STATUT_EN_COURS,
    STATUT_REJETE,
    STATUT_RESOLU,
)

_STATUT_CLASS = {
    STATUT_EN_ATTENTE: "s-wait",
    STATUT_EN_COURS: "s-progress",
    STATUT_RESOLU: "s-done",
    STATUT_REJETE: "s-reject",
    STATUT_CLOTURE: "s-closed",
}

_PRIORITE_CLASS = {
    PRIORITE_BASSE: "p-low",
    PRIORITE_MOYENNE: "p-medium",
    PRIORITE_HAUTE: "p-high",
    PRIORITE_CRITIQUE: "p-critical",
}


def statut_class(statut):
    return _STATUT_CLASS.get(statut, "s-wait")


def priorite_class(priorite):
    return _PRIORITE_CLASS.get(priorite, "p-medium")


def initials(user):
    """Two-letter initials for an avatar chip."""
    if user is None:
        return "?"
    p = (user.prenom or "").strip()
    n = (user.nom or "").strip()
    letters = f"{p[:1]}{n[:1]}".upper()
    return letters or (user.email[:1].upper() if user.email else "?")


def register_ui_helpers(app):
    @app.context_processor
    def _inject():
        from flask import g

        from .services import compter_alertes_non_lues

        return {
            "statut_class": statut_class,
            "priorite_class": priorite_class,
            "initials": initials,
            "nb_alertes_non_lues": compter_alertes_non_lues(getattr(g, "user", None)),
        }
