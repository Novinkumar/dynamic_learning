from seed import seed

from .conftest import login
from app import db
from app.models import Quiz, QuizAttempt, Resource, ResourceCompletion, Topic, User
from app.services.metrics import learning_summary


def test_cold_start_distinguishes_unassessed_topics_from_weak_topics(client, app, user):
    seed(app)
    login(client)

    response = client.get("/api/progress")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["progress"]["resources_completed"] == 0
    assert payload["overall_progress"] == 0.0
    assert payload["weak_topics"] == []
    assert payload["progress"]["assessed_topics"] == 0
    assert all(item["assessed"] is False for item in payload["topic_mastery"])


def test_quiz_response_reports_before_after_adaptation_and_completion_persists(client, app, user):
    seed(app)
    login(client)
    with app.app_context():
        quiz = Quiz.query.join(Topic).filter(Topic.name == "Variables").one()
        answers = {str(question.id): question.answer for question in quiz.questions}
        quiz_id = quiz.id
        resource_id = Resource.query.filter_by(topic_id=quiz.topic_id).first().id
        quiz_payload = client.get(f"/api/quizzes/{quiz_id}").get_json()

    first = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers})
    first_payload = first.get_json()
    adaptation = first_payload["adaptation"]
    assert first.status_code == 200
    assert adaptation["previous_score"] is None
    assert "no quiz history" in adaptation["previous_primary"]["reason"].lower()
    assert adaptation["latest_score"] == 1.0
    assert adaptation["previous_mastery"] == 0.0
    assert adaptation["latest_mastery"] == 0.35
    assert adaptation["mastery_change"] == 0.35
    assert adaptation["next_primary"]
    assert "previous_next_steps" in adaptation and "next_steps" in adaptation

    weaker_answers = {
        str(question["id"]): next(option for option in question["options"] if option != answers[str(question["id"])])
        for question in quiz_payload["questions"]
    }
    second = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": weaker_answers}).get_json()
    assert second["adaptation"]["previous_score"] == 1.0
    assert second["adaptation"]["latest_score"] < 1.0
    assert second["adaptation"]["score_change"] < 0
    assert second["adaptation"]["mastery_change"] < 0

    assert client.post(f"/api/resources/{resource_id}/complete", json={}).get_json()["ok"] is True
    refreshed = client.get("/api/progress").get_json()
    assert refreshed["progress"]["resources_completed"] == 1
    assert refreshed["completed_resource_ids"] == [resource_id]
    assert client.get("/dashboard").status_code == 200


def test_evaluation_route_exposes_observed_and_offline_sections(client, app):
    seed(app)
    with app.app_context():
        admin = User.query.filter_by(email="demo@example.com").one()
    response = client.post("/login", json={"email": admin.email, "password": "password123"})
    assert response.status_code == 200

    payload = client.get("/api/evaluation").get_json()
    assert payload["attempts"] == 0
    assert payload["offline"]["dataset"]["synthetic"] is True
    assert payload["offline"]["dataset"]["labeled_cases"] > 0
    assert set(payload["offline"]["algorithms"]) == {"adaptive", "stable_baseline", "content_based"}
    assert payload["offline"]["algorithms"]["adaptive"]["precision_at_k"] is not None
    page = client.get("/evaluation")
    assert page.status_code == 200
    assert b"synthetic" in page.data.lower()


def test_completion_coverage_is_bounded_by_unique_catalog_resources(app, user, catalog):
    with app.app_context():
        db.session.add_all([
            ResourceCompletion(user_id=user, resource_id=resource_id)
            for resource_id in catalog["resource_ids"]
        ])
        db.session.commit()
        summary = learning_summary(user)
        assert summary["progress"]["resources_completed"] == len(catalog["resource_ids"])
        assert summary["overall_progress"] == 1.0


def test_explicit_seed_reset_returns_a_clean_demo_state(app):
    seed(app)
    with app.app_context():
        learner = User(email="temporary@example.test", name="Temporary")
        learner.set_password("password123")
        db.session.add(learner)
        db.session.commit()
    seed(app, reset=True)
    with app.app_context():
        assert User.query.filter_by(email="temporary@example.test").first() is None
        assert QuizAttempt.query.count() == 0
        assert ResourceCompletion.query.count() == 0
        assert Topic.query.count() == 7
