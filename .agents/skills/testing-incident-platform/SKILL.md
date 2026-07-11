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

Unit tests (fast, cover rules 1-14): `pytest --cov=app --cov-report=term-missing`
(expect ~50 passed, ~94% coverage).

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
