from app import db
import pytest

from seed import seed
from app.models import MasteryScore, Topic, User
from app.routes.common import current_user
from app.services.mastery import get_mastery, update_mastery
from app.services.recommender import recommend_resources


def test_current_user_loads_from_session_and_handles_missing_ids(client, user):
    with client.session_transaction() as session_data:
        session_data["user_id"] = user
    with client:
        client.get("/")
        assert current_user().id == user

    with client.session_transaction() as session_data:
        session_data["user_id"] = 999999
    with client:
        response = client.get("/")
        assert response.get_json()["login"] == "/login"
        assert current_user() is None


def test_admin_route_requires_an_admin_session(client, app, user):
    assert client.get("/api/evaluation").status_code == 401

    client.post("/login", json={"email": "learner@example.test", "password": "correct horse"})
    learner_response = client.get("/api/evaluation")
    assert learner_response.status_code == 403
    assert learner_response.get_json() == {"error": "admin_required"}

    with app.app_context():
        admin = User(email="admin@example.test", name="Test Admin", is_admin=True)
        admin.set_password("admin password")
        db.session.add(admin)
        db.session.commit()

    client.post("/login", json={"email": "admin@example.test", "password": "admin password"})
    admin_response = client.get("/api/evaluation")
    assert admin_response.status_code == 200
    assert "offline" in admin_response.get_json()


def test_learning_rate_sensitivity_changes_estimate_and_recommendation_score(app, user):
    seed(app)
    with app.app_context():
        topic = Topic.query.filter_by(name="Variables").one()
        observed = []
        for rate in (0.2, 0.35, 0.5, 0.8):
            MasteryScore.query.filter_by(user_id=user, topic_id=topic.id).delete()
            db.session.commit()
            update_mastery(user, topic.id, 0.8, learning_rate=rate)
            estimate = get_mastery(user, topic.id)
            priority = next(item.priority for item in recommend_resources(user, 50)
                            if item.topic_id == topic.id)
            observed.append((rate, estimate, priority))

        assert [row[1] for row in observed] == pytest.approx([0.16, 0.28, 0.4, 0.64])
        assert observed[0][2] > observed[-1][2]
