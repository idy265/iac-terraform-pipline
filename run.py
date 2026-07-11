"""Entry point: create the app, seed demo data and run the dev server."""

from app import create_app
from app.extensions import db
from app.seed import seed_demo_data

app = create_app()


@app.cli.command("seed")
def seed_command():
    """Populate the database with demo data."""
    seed_demo_data()
    print("Base de données initialisée avec les données de démonstration.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_demo_data()
    app.run(host="127.0.0.1", port=5000, debug=True)
