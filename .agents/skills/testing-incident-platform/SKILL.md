---
name: testing-incident-platform
description: Test the Flask + SQLite incident / work-order management platform end-to-end. Use when verifying login, declaration lifecycle, role-based access, comments, or admin views.
---

# Testing the Incident / Work-Order Platform

Flask + SQLAlchemy + SQLite app. Business rules live in `app/services.py`; routes in
`app/routes_main.py` / `app/routes_auth.py`; templates in `app/templates/`.

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python run.py            # serves http://127.0.0.1:5000, auto-seeds demo data
```

Unit tests (fast, cover rules 1-14 + alerts/equipements): `pytest --cov=app --cov-report=term-missing`
(expect ~75 passed, ~94% coverage).

To reset to a clean seed before a UI recording, delete the DB first:
`rm -f instance/incidents.db && python run.py`.

## Demo users (seed) — all password `password123`
- `jean@example.com` — Demandeur (owns the seeded Informatique ticket)
- `alice@example.com` — Technicien, specialty Informatique
- `admin@example.com` — Admin

The seed only creates ONE Demandeur and ONE Informatique ticket. To test requester
isolation (Rule 2) and specialty filtering (Rule 3) you must add data first, e.g. via a
short Python snippet inside `app.app_context()`:
- add a 2nd Demandeur (e.g. paul@example.com) to prove a requester gets 403 on another's ticket
- create one Bâtiment-category ticket (as jean) so you can show it's hidden from the Informatique technician and visible to admin

## Golden-path UI flow to record
1. Login: wrong password → banner "Identifiants invalides."; valid → dashboard.
2. "Nouvelle déclaration" → create → detail badge should read exactly **En attente** (Rule 5).
3. As a 2nd requester: dashboard empty; direct `GET /declarations/<id>` of another user's ticket → **403** (Rules 1-2).
4. As the matching-specialty technician: dashboard lists only that specialty; "Prendre en charge" → **En cours** (Rules 3, 7).
5. Resolve: empty "Commentaire final" is blocked; with a comment → **Résolu** + "Résolue le" date, and the comment form disappears (Rules 8, 9, 12).
6. Internal note (checkbox "Note interne") added by technician is visible to tech/admin with an "interne" badge but NOT to the requester.
7. Admin dashboard lists ALL tickets across owners/platforms (Rule 4).

## Alerts & equipment flow (new features)
- **Equipment**: "Nouvelle déclaration" has an optional `equipement_id` select seeded from
  `app/seed.py` (PC bureau 302 / Imprimante étage 3 / Chaudière principale). Selecting one
  shows an "Équipement" row on the detail page (`name (type) · statut`).
- **Alerts** (`app/services.py::_creer_alertes`, `_destinataires_alerte`): filing a declaration
  or posting a *public* comment as the requester notifies matching-specialty technicians +
  admins (never the author). A technician's public comment notifies the requester.
  **Internal notes do NOT notify the requester.** Sidebar "Alertes" shows a red unread badge
  (`nb_alertes_non_lues` via `app/ui.py`); `/alertes` lists them; clicking one marks it read
  (badge decrements) and redirects to the declaration; "Tout marquer comme lu" clears the badge.
- To record the alert golden path: create a declaration + comment as `jean`, then log in as
  `alice` to see the badge/page, click an alert (badge decrements), post an internal note as
  `alice`, and confirm `jean` still has "Aucune alerte".
- Note: the seed already generates alerts for the initial declaration, so `alice` starts with
  a non-zero badge even before you create new data.

## UI (professional redesign)
- Layout is a sidebar app shell (`app/templates/base.html`) + a stylesheet at
  `app/static/style.css`; status/priority CSS classes and avatar initials come from a Jinja
  context processor in `app/ui.py` (`statut_class`, `priorite_class`, `initials`).
- Dashboard shows KPI stat tiles computed in `dashboard.html` via `selectattr` over the
  visible declarations — the numbers should match the seeded/visible data, not be blank.
- 403/404 are rendered by `register_error_handlers` in `app/__init__.py` using
  `error.html` (only for logged-in users; anonymous falls back to the default page).
- For a good demo screenshot, seed several declarations with varied statuses/priorities
  (En attente / En cours / Résolu, Basse→Critique) so badges/pills and KPI tiles are visible.

## Gotchas / notes
- The resolve "Commentaire final" textarea has HTML5 `required`, so an empty submit is
  blocked **client-side** in the browser — the server-side Rule 8 guard is proven by the
  unit tests, not by the browser step. Note this in reports.
- SQLite FK cascade (Rule 14) needs `PRAGMA foreign_keys=ON`; the app sets this via a
  SQLAlchemy `connect` event listener in `app/__init__.py`. If cascade tests fail, check
  that listener is firing.
- The local DB file persists between `run.py` restarts (default `instance/incidents.db`
  or `incidents.db`). Delete it to reset to a clean seed if test data accumulates.
- Repo is named `iac-terraform-pipline` but contains this Python app, not Terraform.

## Devin Secrets Needed
None — the app runs fully locally with SQLite and seeded demo credentials.
