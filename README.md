# Plateforme de Gestion des Incidents et Demandes de Travaux

Outil de déclaration des incidents / demandes de travaux et de leur suivi
(informatique **et** bâtiment), construit avec **Flask + SQLAlchemy + SQLite**.

## Fonctionnalités

- Authentification par session (mots de passe hachés via Werkzeug).
- Rôles : **Demandeur**, **Technicien** (avec spécialité *Informatique* ou
  *Bâtiment*) et **Administrateur**.
- Cycle de vie complet des déclarations (ticket) : `En attente` → `En cours`
  → `Résolu` / `Rejeté`.
- Commentaires (avec notes internes réservées aux techniciens), pièces jointes
  et historique des changements de statut (SLA).
- Règles métier 1 à 14 de la spécification implémentées dans
  [`app/services.py`](app/services.py) et couvertes par des tests unitaires.

## Modèle de données

Voir [`schema.sql`](schema.sql) pour le schéma relationnel documenté et
[`app/models.py`](app/models.py) pour les modèles SQLAlchemy :
`roles`, `utilisateurs`, `sites`, `emplacements`, `categories`, `declarations`,
`commentaires`, `pieces_jointes`, `historique_statuts`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l'application

```bash
python run.py
```

Puis ouvrir http://127.0.0.1:5000. La base est initialisée automatiquement avec
des données de démonstration.

Identifiants de test :

| Rôle       | Email               | Mot de passe   |
|------------|---------------------|----------------|
| Demandeur  | jean@example.com    | password123    |
| Technicien | alice@example.com   | password123    |
| Admin      | admin@example.com   | password123    |

## Tests

```bash
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

Les tests couvrent les modèles, la couche de service (règles métier 1-14) et
les routes web.

## Règles métier implémentées

| Règle | Description | Implémentation |
|-------|-------------|----------------|
| 1-2 | Un demandeur ne voit que ses propres déclarations | `can_view_declaration` |
| 3 | Un technicien ne traite que sa spécialité | `can_view_declaration`, `prendre_en_charge` |
| 4 | L'admin a tous les droits | `can_view_declaration` |
| 5 | Statut initial « En attente » | `create_declaration` |
| 6 | Site + emplacement + catégorie obligatoires | `create_declaration` |
| 7 | Prise en charge → « En cours » + `technicien_id` | `prendre_en_charge` |
| 8 | Commentaire final obligatoire pour résoudre/rejeter | `resoudre` / `rejeter` |
| 9 | `date_resolution` renseignée automatiquement | `resoudre` / `rejeter` |
| 10 | Seul l'auteur ou un admin modifie/supprime un commentaire | `modifier_commentaire` / `supprimer_commentaire` |
| 11 | Pièces jointes optionnelles | `ajouter_piece_jointe` |
| 12 | Pas de nouveau contenu sur un ticket clôturé | `ajouter_commentaire` / `ajouter_piece_jointe` |
| 13 | Suppression d'un utilisateur → anonymisation, historique conservé | `anonymiser_utilisateur` |
| 14 | Emplacement rattaché à un site ; suppression en cascade | modèles `Site` / `Emplacement` |
