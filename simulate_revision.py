
from datetime import timedelta
from sqlalchemy.engine import make_url

from app import create_app, db
from app.models import User, ResourceCompletion, utcnow_naive
from config import DEMO_ACCOUNT_EMAIL


def main():
    app = create_app()

    with app.app_context():
        environment = str(app.config.get("APP_ENV", "")).strip().lower()
        database_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])

        # Safety checks: never modify a production database.
        if environment == "production" or database_url.get_backend_name() != "sqlite":
            raise RuntimeError(
                "This test is allowed only on a non-production SQLite database."
            )

        user = User.query.filter_by(email=DEMO_ACCOUNT_EMAIL).first()

        if user is None:
            print("Demo account not found. Check config.py and seed.py.")
            return

        completion = (
            ResourceCompletion.query
            .filter_by(user_id=user.id)
            .order_by(ResourceCompletion.id.asc())
            .first()
        )

        if completion is None:
            print("No completed resources found for the demo learner.")
            print("Complete a resource in the Library, then run this script again.")
            return

        old_date = completion.completed_at
        completion.completed_at = utcnow_naive() - timedelta(days=15)

        db.session.commit()

        print("Revision test data updated successfully.")
        print(f"Learner: {user.name}")
        print(f"Resource: {completion.resource.title}")
        print(f"Previous completion date: {old_date}")
        print(f"Simulated completion date: {completion.completed_at}")
        print("Simulated age: 15 days")


if __name__ == "__main__":
    main()
