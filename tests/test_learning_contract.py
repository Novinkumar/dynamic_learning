from .conftest import login
from app import db
from app.models import MasteryScore, ResourceCompletion
from app.services.mastery import get_mastery
from app.services.metrics import evaluation_metrics
from app.services.recommender import recommend_resources


def test_cold_start_returns_catalog_and_excludes_completed(client, app, user, catalog):
    login(client)
    response = client.get("/api/resources?limit=10")
    assert response.status_code == 200
    assert {item["id"] for item in response.get_json()["resources"]} == set(catalog["resource_ids"])

    with app.app_context():
        db.session.add(ResourceCompletion(user_id=user, resource_id=catalog["resource_ids"][0]))
        db.session.commit()
        remaining = recommend_resources(user, 10)
        assert [item.id for item in remaining] == [catalog["resource_ids"][1]]


def test_quiz_scoring_updates_mastery_and_changes_recommendations(client, app, user, catalog):
    login(client)
    quiz_id = catalog["quiz_id"]
    answers = dict(zip((str(item) for item in catalog["question_ids"]), catalog["answers"]))
    response = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["correct"] == 2 and payload["total"] == 2 and payload["score"] == 1.0
    with app.app_context():
        assert get_mastery(user, catalog["topic_id"]) == 0.35


def test_low_mastery_prerequisite_is_ranked_before_advanced_topic(app, user, catalog):
    with app.app_context():
        db.session.add_all([
            MasteryScore(user_id=user, topic_id=catalog["topic_id"], score=0.15),
            MasteryScore(user_id=user, topic_id=catalog["advanced_id"], score=0.9),
        ])
        db.session.commit()
        ranked = recommend_resources(user, 2)
        assert ranked[0].id == catalog["resource_ids"][0]


def test_revision_signal_removes_completed_resource_from_next_queue(app, user, catalog):
    with app.app_context():
        db.session.add(ResourceCompletion(user_id=user, resource_id=catalog["resource_ids"][0]))
        db.session.commit()
        assert catalog["resource_ids"][0] not in [item.id for item in recommend_resources(user, 10)]


def test_partial_quiz_is_scored_per_question(client, catalog, user):
    login(client)
    question_id = catalog["question_ids"][0]
    response = client.post(f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": {str(question_id): catalog["answers"][0]}})
    assert response.status_code == 200
    assert response.get_json()["score"] == 0.5


def test_metrics_are_zero_for_cold_start(app):
    with app.app_context():
        assert evaluation_metrics() == {"attempts": 0, "mean_score": 0.0, "completion_rate": 0.0}


def test_invalid_answer_payload_is_rejected(client, catalog, user):
    login(client)
    response = client.post(f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": []})
    assert response.status_code == 400
    assert "answers" in response.get_json()["error"]
