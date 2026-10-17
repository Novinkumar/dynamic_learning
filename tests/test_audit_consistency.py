"""Focused audit regressions; every database here is explicitly in-memory."""

from datetime import datetime, timedelta
import re

from flask import template_rendered
import pytest

from app import create_app, db
from app.models import (
    MasteryScore, Question, QuestionResponse, Quiz, QuizAttempt,
    ResourceCompletion, User,
)
from app.routes import learning
from app.services.mastery import topic_mastery, update_mastery
from app.services.metrics import learning_summary, ndcg_at_k, precision_at_k, recall_at_k
from app.services.offline_evaluation import ranking_metrics
from config import TestingConfig


@pytest.fixture()
def app():
    class AuditConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    application = create_app(AuditConfig)
    with application.app_context():
        assert db.engine.url.database == ":memory:"
        yield application
        db.session.remove()
        db.drop_all()
        db.session.remove()
        for engine in db.engines.values():
            engine.dispose()


@pytest.fixture()
def learner_client(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user
    return client


def _answers(catalog):
    return dict(zip(map(str, catalog["question_ids"]), catalog["answers"]))


def _assert_no_submission():
    assert QuizAttempt.query.count() == 0
    assert QuestionResponse.query.count() == 0
    assert MasteryScore.query.count() == 0


def test_library_refresh_keeps_only_current_learners_completed_badges(
    app, learner_client, user, catalog,
):
    own_resource, other_resource = catalog["resource_ids"]
    other = User(email="other@example.test", name="Other", password_hash="unused")
    db.session.add(other)
    db.session.flush()
    db.session.add(ResourceCompletion(user_id=other.id, resource_id=other_resource))
    db.session.commit()
    assert learner_client.post(f"/api/resources/{own_resource}/complete").status_code == 200

    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        for _ in range(2):
            response = learner_client.get("/library")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            for resource_id, completed in ((own_resource, True), (other_resource, False)):
                card = re.search(
                    rf'<article[^>]*data-resource-card="{resource_id}".*?</article>',
                    html, re.DOTALL,
                ).group()
                badge = re.search(r'<span[^>]*data-completed-badge[^>]*>', card).group()
                button = re.search(r'<button[^>]*type="submit"[^>]*>', card).group()
                assert ("hidden" not in badge) is completed
                assert ("disabled" in button) is completed
            assert contexts[-1]["user"].id == user
            assert set(contexts[-1]["completed_resource_ids"]) == {own_resource}


@pytest.mark.parametrize("body", ["", "{", "null", "[]", "[1]", '"answers"', "true", "0", "12"])
def test_quiz_rejects_bad_or_non_object_json(learner_client, catalog, body):
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", data=body, content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]
    _assert_no_submission()


@pytest.mark.parametrize("answers", [None, [], "Retrieval", 1])
def test_quiz_rejects_non_object_answers(learner_client, catalog, answers):
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": answers},
    )
    assert response.status_code == 400
    assert "answers" in response.get_json()["error"]
    _assert_no_submission()


@pytest.mark.parametrize("answer", [7, True, None, ["Retrieval"], {"value": "Retrieval"},
                                   "retrieval", " Retrieval ", "", "not an option"])
def test_quiz_rejects_non_string_or_non_option_answers(learner_client, catalog, answer):
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit",
        json={"answers": {str(catalog["question_ids"][0]): answer}},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]
    _assert_no_submission()


@pytest.mark.parametrize("foreign_question", [False, True])
def test_quiz_rejects_unknown_question_ids(learner_client, catalog, foreign_question):
    question_id = "999999"
    if foreign_question:
        other_quiz = Quiz(topic_id=catalog["topic_id"], title="Another quiz")
        question = Question(quiz=other_quiz, prompt="Other?", options=["Retrieval"], answer="Retrieval")
        db.session.add(question)
        db.session.commit()
        question_id = str(question.id)
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": {question_id: "Retrieval"}},
    )
    assert response.status_code == 400
    _assert_no_submission()


@pytest.mark.parametrize("chosen,correct", [("True", True), ("true", False), (" True ", False)])
def test_quiz_scores_chosen_options_exactly(learner_client, catalog, chosen, correct):
    question_id = catalog["question_ids"][0]
    question = db.session.get(Question, question_id)
    question.options = ["True", "true", " True "]
    question.answer = "True"
    db.session.commit()
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": {str(question_id): chosen}},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["correct"] == int(correct)
    assert payload["score"] == int(correct) / 2
    feedback = next(item for item in payload["feedback"] if item["question_id"] == question_id)
    assert feedback["answer"] == chosen
    assert feedback["correct"] is correct
    recorded = QuestionResponse.query.filter_by(question_id=question_id).one()
    assert recorded.answer == chosen
    assert recorded.is_correct is correct


@pytest.mark.parametrize("include_answer", [False, True])
def test_partial_answers_remain_incorrect_and_are_recorded(learner_client, catalog, include_answer):
    answers = {str(catalog["question_ids"][0]): catalog["answers"][0]} if include_answer else {}
    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": answers},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["correct"] == int(include_answer)
    assert payload["score"] == int(include_answer) / 2
    attempt = db.session.get(QuizAttempt, payload["attempt_id"])
    assert attempt.answers == answers
    assert len(attempt.responses) == 2
    omitted = [item for item in attempt.responses if str(item.question_id) not in answers]
    assert all(item.answer == "" and item.is_correct is False for item in omitted)


@pytest.mark.parametrize("cache_state", ["missing", "stale", "manual"])
def test_submission_cache_matches_replayed_mastery(learner_client, catalog, user, cache_state):
    if cache_state != "manual":
        completed_at = datetime(2020, 1, 1)
        db.session.add_all([
            QuizAttempt(user_id=user, quiz_id=catalog["quiz_id"], score=score,
                        answers={}, completed_at=completed_at + timedelta(days=index))
            for index, score in enumerate((1.0, 0.0))
        ])
    if cache_state != "missing":
        db.session.add(MasteryScore(user_id=user, topic_id=catalog["topic_id"], score=0.9))
    db.session.commit()

    response = learner_client.post(
        f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": _answers(catalog)},
    )
    assert response.status_code == 200
    payload = response.get_json()
    expected = 0.35 if cache_state == "manual" else 0.4979
    assert payload["mastery"] == expected
    assert payload["adaptation"]["latest_mastery"] == expected
    db.session.remove()
    assert MasteryScore.query.filter_by(user_id=user, topic_id=catalog["topic_id"]).one().score == expected
    assert topic_mastery(user, catalog["topic_id"]) == expected
    assert learning_summary(user)["mastery"][catalog["topic_id"]] == expected


def test_mastery_replays_timestamp_then_id_across_topic_quizzes(app, user, catalog):
    another_quiz = Quiz(topic_id=catalog["topic_id"], title="Second assessment")
    other_topic_quiz = Quiz(topic_id=catalog["advanced_id"], title="Different topic")
    db.session.add_all([another_quiz, other_topic_quiz])
    db.session.flush()
    timestamp = datetime(2020, 1, 1)
    db.session.add_all([
        QuizAttempt(id=30, user_id=user, quiz_id=catalog["quiz_id"], score=1.0,
                    answers={}, completed_at=timestamp),
        QuizAttempt(id=20, user_id=user, quiz_id=catalog["quiz_id"], score=1.0,
                    answers={}, completed_at=timestamp + timedelta(days=1)),
        QuizAttempt(id=10, user_id=user, quiz_id=another_quiz.id, score=0.0,
                    answers={}, completed_at=timestamp + timedelta(days=1)),
        QuizAttempt(user_id=user, quiz_id=other_topic_quiz.id, score=0.0,
                    answers={}, completed_at=timestamp),
        MasteryScore(user_id=user, topic_id=catalog["topic_id"], score=0.99),
    ])
    db.session.commit()
    assert topic_mastery(user, catalog["topic_id"]) == 0.4979
    for _ in range(2):
        # Existing evidence is authoritative, even with a stale cache or a caller's synthetic rate.
        cached = update_mastery(user, catalog["topic_id"], 0.0, learning_rate=0.8)
        assert cached.score == 0.4979
        assert topic_mastery(user, catalog["topic_id"]) == cached.score


def test_no_attempt_mastery_keeps_manual_rate_and_commit_control(app, user, catalog):
    db.session.add(MasteryScore(user_id=user, topic_id=catalog["topic_id"], score=0.4))
    db.session.commit()
    assert update_mastery(user, catalog["topic_id"], 0.8, learning_rate=0.5, commit=False).score == 0.6
    db.session.flush()
    db.session.rollback()
    assert topic_mastery(user, catalog["topic_id"]) == 0.4
    assert update_mastery(user, catalog["topic_id"], 0.8, learning_rate=0.5).score == 0.6
    db.session.remove()
    assert topic_mastery(user, catalog["topic_id"]) == 0.6


@pytest.mark.parametrize("existing_cache", [False, True])
def test_failed_mastery_write_rolls_back_attempt_responses_and_cache(
    learner_client, catalog, user, monkeypatch, existing_cache,
):
    if existing_cache:
        db.session.add(MasteryScore(user_id=user, topic_id=catalog["topic_id"], score=0.8))
        db.session.commit()

    def fail_after_cache_write(*args, **kwargs):
        kwargs["commit"] = False
        update_mastery(*args, **kwargs)
        db.session.flush()
        raise RuntimeError("simulated mastery write failure")

    monkeypatch.setattr(learning, "update_mastery", fail_after_cache_write)
    with pytest.raises(RuntimeError, match="simulated mastery write failure"):
        learner_client.post(
            f"/api/quizzes/{catalog['quiz_id']}/submit", json={"answers": _answers(catalog)},
        )
    db.session.remove()
    assert QuizAttempt.query.count() == 0
    assert QuestionResponse.query.count() == 0
    cached = MasteryScore.query.filter_by(user_id=user, topic_id=catalog["topic_id"]).first()
    if existing_cache:
        assert cached.score == 0.8
    else:
        assert cached is None


@pytest.mark.parametrize("recommended,relevant,k", [
    ([1], [1], 5), ([1, 2, 3], [2, 3], 2), ([], [1], 5),
    ([1], [], 5), ([1], None, 5),
])
def test_ranking_helpers_share_offline_definitions(recommended, relevant, k):
    expected = ranking_metrics(recommended, relevant, k)
    actual = {
        "precision_at_k": precision_at_k(recommended, relevant, k),
        "recall_at_k": recall_at_k(recommended, relevant, k),
        "ndcg_at_k": ndcg_at_k(recommended, relevant, k),
    }
    assert actual == expected


@pytest.mark.parametrize("metric", [precision_at_k, recall_at_k, ndcg_at_k])
@pytest.mark.parametrize("recommended,k", [([1], 0), ([1], -1), ([1], True), ([1, 1], 5)])
def test_ranking_helpers_share_input_validation(metric, recommended, k):
    with pytest.raises(ValueError):
        metric(recommended, [1], k)
