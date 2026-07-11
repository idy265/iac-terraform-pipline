"""Domain constants for the incident / work-order management platform."""

# Declaration lifecycle statuses (Rules 5, 7, 8, 9, 12)
STATUT_EN_ATTENTE = "En attente"
STATUT_EN_COURS = "En cours"
STATUT_RESOLU = "Résolu"
STATUT_REJETE = "Rejeté"
STATUT_CLOTURE = "Clôturé"

STATUTS = (
    STATUT_EN_ATTENTE,
    STATUT_EN_COURS,
    STATUT_RESOLU,
    STATUT_REJETE,
    STATUT_CLOTURE,
)

# Statuses that mean a declaration is finished and read-only for new content (Rule 12)
STATUTS_TERMINES = (STATUT_RESOLU, STATUT_REJETE, STATUT_CLOTURE)

# Priorities
PRIORITE_BASSE = "Basse"
PRIORITE_MOYENNE = "Moyenne"
PRIORITE_HAUTE = "Haute"
PRIORITE_CRITIQUE = "Critique"

PRIORITES = (PRIORITE_BASSE, PRIORITE_MOYENNE, PRIORITE_HAUTE, PRIORITE_CRITIQUE)

# User profiles / roles
ROLE_DEMANDEUR = "Demandeur"
ROLE_TECHNICIEN = "Technicien"
ROLE_ADMIN = "Admin"

ROLES = (ROLE_DEMANDEUR, ROLE_TECHNICIEN, ROLE_ADMIN)

# Platform types used to route incidents to the right technician (Rule 3)
PLATEFORME_INFORMATIQUE = "Informatique"
PLATEFORME_BATIMENT = "Bâtiment"

PLATEFORMES = (PLATEFORME_INFORMATIQUE, PLATEFORME_BATIMENT)
