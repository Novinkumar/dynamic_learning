"""Acceptance coverage for the seeded Python learning loop."""

from seed import seed

from .conftest import login
from app import db
from app.models import Quiz, Topic
from app.services.recommender import recommend_resources


def test_seed_has_seven_topics_prerequisites_resources_and_real_python_quizzes(app):
    seed(app)
    with app.app_context():
        assert Topic.query.count() == 7
        assert all(topic.resources for topic in Topic.query.all())
        assert sum(len(topic.prerequisites) for topic in Topic.query.all()) >= 8
        for name in ("Variables", "Conditionals", "Loops", "Functions"):
            topic = Topic.query.filter_by(name=name).one()
            quiz = Quiz.query.filter_by(topic_id=topic.id).one()
            assert len(quiz.questions) >= 3
            assert len({question.prompt for question in quiz.questions}) == len(quiz.questions)
            assert all(len(question.options) >= 3 for question in quiz.questions)


def test_progress_scores_weak_topics_history_and_explanations_are_readable(client, app, user):
    seed(app)
    login(client)

    before = client.get("/api/progress")
    assert before.status_code == 200
    cold = before.get_json()
    assert cold["progress"]["quizzes_completed"] == 0
    assert len(cold["topic_mastery"]) == 7
    assert cold["weak_topics"] == []
    assert all(item["assessed"] is False for item in cold["topic_mastery"])
    assert cold["recommendations"]
    assert all(item["explanation"] for item in cold["recommendations"])

    with app.app_context():
        quiz = Quiz.query.join(Topic).filter(Topic.name == "Variables").one()
        correct_answers = {str(question.id): question.answer for question in quiz.questions}
        quiz_id = quiz.id

    first = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": correct_answers}).get_json()
    assert first["total"] >= 3
    assert len(first["feedback"]) == first["total"]
    assert all(item["explanation"] for item in first["feedback"])
    assert first["recommendations"]

    history = client.get("/api/quiz-history").get_json()["history"]
    assert len(history) == 1
    assert history[0]["topic"] == "Variables"
    assert history[0]["score"] == 1.0
    mastery = client.get("/api/topic-mastery").get_json()["topics"]
    variables = next(item for item in mastery if item["topic"] == "Variables")
    assert variables["mastery"] == 0.35


def test_resource_api_exposes_learning_metadata_and_completion_progress(client, app, user):
    seed(app)
    login(client)
    with app.app_context():
        variables = Topic.query.filter_by(name="Variables").one()
        topic_id = variables.id

    response = client.get(f"/api/resources?topic={topic_id}&limit=10")
    assert response.status_code == 200
    resources = response.get_json()["resources"]
    assert len(resources) == 3
    assert all(item["url"].startswith("http") and item["description"] for item in resources)

    completed_id = resources[0]["id"]
    assert client.post(f"/api/resources/{completed_id}/complete", json={}).get_json()["ok"] is True
    progress = client.get("/api/progress").get_json()["progress"]
    assert progress["resources_completed"] == 1


def test_recommendation_priority_changes_as_quiz_history_accumulates(client, app, user):
    seed(app)
    login(client)
    with app.app_context():
        quiz = Quiz.query.join(Topic).filter(Topic.name == "Variables").one()
        answers = {str(question.id): question.answer for question in quiz.questions}
        quiz_id = quiz.id
        initial = recommend_resources(user, 20)
        initial_priority = next(item.priority for item in initial if item.topic.name == "Variables")
        initial_order = [item.id for item in initial]

    # Repeated evidence moves Variables from the weak-topic queue toward mastery.
    for _ in range(3):
        response = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers})
        assert response.status_code == 200

    with app.app_context():
        updated = recommend_resources(user, 20)
        updated_priority = next(item.priority for item in updated if item.topic.name == "Variables")
        updated_order = [item.id for item in updated]
        assert updated_priority < initial_priority
        assert updated_order != initial_order
        assert db.session.query(Topic).count() == 7
