"""Acceptance tests for fresh, private, longer AI practice sessions."""

import json

import pytest
from sqlalchemy import inspect, text

from app import db
from app.models import Quiz, QuizAttempt, Question, Topic, User
from app.services import quiz_ai
from app.services.question_bank import generate_offline_questions, supported_topics
from app.services.schema import ensure_schema
from seed import seed

from .conftest import login


@pytest.mark.parametrize("topic", supported_topics())
@pytest.mark.parametrize("difficulty", ["foundation", "core", "stretch"])
def test_offline_generator_creates_twenty_fresh_validated_questions(topic, difficulty):
    questions = generate_offline_questions(topic, count=20, difficulty=difficulty)
    assert len(questions) == 20
    assert len({item["prompt"] for item in questions}) == 20
    for item in questions:
        assert item["topic"] == topic
        assert len(item["options"]) == 4
        assert len(set(item["options"])) == 4
        assert item["answer"] in item["options"]
        assert item["explanation"] and item["skill"]
        assert item["difficulty"] in {"foundation", "core", "stretch"}


def test_ai_practice_workflow_creates_longer_private_sessions(client, app, user):
    seed(app)
    login(client)
    practice = client.get("/practice")
    assert practice.status_code == 200
    assert b"AI PRACTICE STUDIO" in practice.data
    assert b"Offline AI generator active" in practice.data

    with app.app_context():
        topic = Topic.query.filter_by(name="Variables").one()
        topic_id = topic.id

    first = client.post("/practice/generate", data={
        "topic_id": topic_id, "length": 12, "difficulty": "adaptive",
    })
    assert first.status_code == 303
    assert "/quiz/" in first.headers["Location"]

    with app.app_context():
        quiz = Quiz.query.filter_by(source="generated").order_by(Quiz.id.desc()).one()
        quiz_id = quiz.id
        assert quiz.owner_id == user
        assert quiz.generation_mode == "foundation"
        assert len(quiz.questions) == 12
        assert len({question.prompt for question in quiz.questions}) == 12
        assert all(question.explanation and question.skill for question in quiz.questions)
        first_prompts = {question.prompt for question in quiz.questions}
        answers = {str(question.id): question.answer for question in quiz.questions}
        assert Quiz.query.filter_by(source="catalog").count() == 7

    page = client.get(f"/quiz/{quiz_id}")
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    assert b"data-quiz-wizard" in page.data
    assert b"data-answer" not in page.data

    api = client.get(f"/api/quizzes/{quiz_id}").get_json()
    assert api["question_count"] == 12
    assert api["one_time"] is True
    assert all("answer" not in question and "explanation" not in question
               for question in api["questions"])

    submitted = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers})
    payload = submitted.get_json()
    assert submitted.status_code == 200
    assert payload["score"] == 1.0 and payload["total"] == 12
    assert payload["mastery"] == 0.35
    assert payload["source"] == "generated"
    assert len(payload["feedback"]) == 12
    assert all(item["skill"] and item["explanation"] for item in payload["feedback"])

    duplicate = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers})
    assert duplicate.status_code == 409

    second = client.post("/practice/generate", data={
        "topic_id": topic_id, "length": 12, "difficulty": "core",
    })
    assert second.status_code == 303
    with app.app_context():
        quiz2 = Quiz.query.filter_by(source="generated").order_by(Quiz.id.desc()).first()
        assert quiz2.id != quiz_id
        assert len(quiz2.questions) == 12
        second_prompts = {question.prompt for question in quiz2.questions}
        # Recent prompts are deliberately skipped; with this bank the overlap
        # should be zero for two consecutive sessions.
        assert not (first_prompts & second_prompts)
        assert QuizAttempt.query.filter_by(quiz_id=quiz_id).count() == 1


def test_generated_quiz_is_private_to_its_owner(client, app, user):
    seed(app)
    login(client)
    with app.app_context():
        topic = Topic.query.filter_by(name="Loops").one()
        topic_id = topic.id
    client.post("/practice/generate", data={
        "topic_id": topic_id, "length": 8, "difficulty": "core",
    })
    with app.app_context():
        quiz_id = Quiz.query.filter_by(source="generated").order_by(Quiz.id.desc()).first().id
        other = User(email="other-ai@example.test", name="Other Learner")
        other.set_password("another correct horse")
        db.session.add(other)
        db.session.commit()

    other_client = app.test_client()
    assert other_client.post("/login", data={
        "email": "other-ai@example.test", "password": "another correct horse",
    }).status_code == 302
    assert other_client.get(f"/quiz/{quiz_id}").status_code == 404
    assert other_client.get(f"/api/quizzes/{quiz_id}").status_code == 404
    assert other_client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": {}}).status_code == 404


@pytest.mark.parametrize("mastery,expected", [(0.0, "foundation"), (0.45, "core"), (0.8, "stretch")])
def test_adaptive_difficulty_uses_recorded_mastery(mastery, expected):
    assert quiz_ai.choose_difficulty(mastery, "adaptive") == expected
    assert quiz_ai.choose_difficulty(mastery, "core") == "core"


def test_live_provider_http_payload_is_parsed_without_exposing_answers(monkeypatch):
    config = {
        "AI_API_KEY": "test-key", "AI_API_BASE": "https://ai.example.test/v1",
        "AI_MODEL": "test-model", "AI_TIMEOUT": 10,
    }
    content = """```json
    {"questions":[
      {"prompt":"What is printed by print(2 + 2)?","options":["3","4","5","22"],"answer":"4","explanation":"Two plus two equals four.","skill":"Arithmetic","difficulty":"foundation"},
      {"prompt":"What is printed by print(3 * 3)?","options":["6","9","3","33"],"answer":"9","explanation":"Three multiplied by three equals nine.","skill":"Arithmetic","difficulty":"core"}
    ]}
    ```"""
    response_payload = {"choices": [{"message": {"content": content}}]}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(response_payload).encode("utf-8")

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(quiz_ai.urllib.request, "urlopen", fake_urlopen)
    questions = quiz_ai._call_live_ai(
        config, "Variables", 2, "core", 0.4, None, [], "nonce", __import__("random").Random(1),
    )
    assert captured["url"] == "https://ai.example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["timeout"] == 10
    assert len(questions) == 2
    assert all(item["source"] == "live_ai" for item in questions)
    assert all(item["answer"] in item["options"] for item in questions)
    assert "test-key" not in json.dumps(questions)


def test_live_ai_questions_are_validated_and_provider_failure_falls_back(monkeypatch):
    config = {
        "AI_API_KEY": "test-key", "AI_API_BASE": "https://ai.example.test/v1",
        "AI_MODEL": "test-model", "AI_TIMEOUT": 10,
    }

    def valid_provider(*args, **kwargs):
        config, topic, count, difficulty, mastery, recent_score, recent_prompts, nonce, rng = args
        return [{
            "prompt": f"Live question {index}: what is printed by print({index} + 1)?",
            "options": [str(index + 1), str(index), str(index + 2), "None"],
            "answer": str(index + 1),
            "explanation": "Python evaluates the addition before printing the result.",
            "skill": "Expressions",
            "difficulty": difficulty,
            "source": "live_ai",
            "topic": topic,
        } for index in range(count)]

    monkeypatch.setattr(quiz_ai, "_call_live_ai", valid_provider)
    live = quiz_ai.generate_quiz(config, "Variables", count=6, difficulty="core")
    assert live.provider == "live_ai" and live.live is True
    assert len(live.questions) == 6
    assert all(item["source"] == "live_ai" for item in live.questions)

    def broken_provider(*args, **kwargs):
        raise quiz_ai.AIQuizGenerationError("simulated provider failure")

    monkeypatch.setattr(quiz_ai, "_call_live_ai", broken_provider)
    fallback = quiz_ai.generate_quiz(config, "Variables", count=6, difficulty="core")
    assert fallback.provider == "offline_fallback"
    assert fallback.live is False
    assert "offline generator" in fallback.warning.lower()
    assert len(fallback.questions) == 6

    bad_payload = {"questions": [{"prompt": "Too short?", "options": ["a", "b"],
                                  "answer": "a", "explanation": "Because."}]}
    with pytest.raises(quiz_ai.AIQuizGenerationError):
        quiz_ai._validate_live_questions(bad_payload, 1, "Variables", "core", __import__("random").Random(1), [])


def test_generation_route_records_the_live_provider_label(client, app, user, monkeypatch):
    seed(app)
    login(client)
    from app.routes import learning

    def fake_generate_quiz(config, topic, **kwargs):
        count = kwargs["count"]
        return quiz_ai.GenerationResult(
            questions=generate_offline_questions(topic, count=count, difficulty="core"),
            provider="live_ai", model="guide-demo-model",
            requested_difficulty="core", effective_difficulty="core",
            seed="test-seed", live=True,
        )

    monkeypatch.setattr(learning, "generate_quiz", fake_generate_quiz)
    with app.app_context():
        topic_id = Topic.query.filter_by(name="Functions").one().id
    response = client.post("/practice/generate", data={
        "topic_id": topic_id, "length": 8, "difficulty": "core",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Live AI" in response.data
    with app.app_context():
        quiz = Quiz.query.filter_by(source="generated").one()
        assert quiz.generation_provider == "live_ai"
        assert quiz.generation_model == "guide-demo-model"
        assert len(quiz.questions) == 8


def test_unsupported_topic_without_live_ai_fails_gracefully(client, app, user):
    seed(app)
    login(client)
    with app.app_context():
        topic = Topic(name="Quantum Computing", description="A topic outside the offline bank.")
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id

    response = client.post("/practice/generate", data={
        "topic_id": topic_id, "length": 10, "difficulty": "adaptive",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"offline generator supports" in response.data or b"Could not generate" in response.data
    with app.app_context():
        assert Quiz.query.filter_by(source="generated").count() == 0


def test_legacy_sqlite_schema_is_upgraded_idempotently(tmp_path):
    """Existing quiz/question tables gain AI columns without data loss."""
    from flask import Flask

    database = tmp_path / "legacy.sqlite3"
    legacy_app = Flask("legacy_schema_test")
    legacy_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database.as_posix()}"
    legacy_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(legacy_app)
    with legacy_app.app_context():
        with db.engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE quiz (
                    id INTEGER PRIMARY KEY,
                    topic_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL
                )
            """))
            connection.execute(text("""
                CREATE TABLE question (
                    id INTEGER PRIMARY KEY,
                    quiz_id INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    options JSON NOT NULL,
                    answer VARCHAR(255) NOT NULL
                )
            """))
            connection.execute(text("INSERT INTO quiz (id, topic_id, title) VALUES (1, 1, 'Legacy check')"))
            connection.execute(text("INSERT INTO question (id, quiz_id, prompt, options, answer) VALUES (1, 1, 'Legacy prompt', '[\"a\", \"b\"]', 'a')"))
        ensure_schema()
        ensure_schema()
        quiz_columns = {column["name"] for column in inspect(db.engine).get_columns("quiz")}
        question_columns = {column["name"] for column in inspect(db.engine).get_columns("question")}
        assert {"source", "owner_id", "generation_provider", "created_at", "completed_at"} <= quiz_columns
        assert {"explanation", "skill", "difficulty"} <= question_columns
        with db.engine.connect() as connection:
            assert connection.execute(text("SELECT source FROM quiz WHERE id = 1")).scalar() == "catalog"
            assert connection.execute(text("SELECT explanation FROM question WHERE id = 1")).scalar() == ""
        db.session.remove()
        db.engine.dispose()
