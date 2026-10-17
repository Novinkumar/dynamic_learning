import pytest

from config import TestingConfig
from app import create_app, db
from app.models import Question, Quiz, Resource, Topic, User


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        yield application
        db.session.remove()
        db.drop_all()
        db.session.remove()
        for engine in db.engines.values():
            engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def catalog(app):
    with app.app_context():
        topic = Topic(name="Foundations")
        advanced = Topic(name="Applications")
        db.session.add_all([topic, advanced])
        db.session.flush()
        resources = [
            Resource(topic_id=topic.id, title="Retrieval practice", url="https://example.test/retrieval", kind="article", difficulty=1),
            Resource(topic_id=advanced.id, title="Applied practice", url="https://example.test/applied", kind="exercise", difficulty=3),
        ]
        quiz = Quiz(topic_id=topic.id, title="Foundations check")
        db.session.add_all([*resources, quiz])
        db.session.flush()
        db.session.add_all([
            Question(quiz_id=quiz.id, prompt="What supports retention?", options=["Retrieval", "Avoidance"], answer="Retrieval"),
            Question(quiz_id=quiz.id, prompt="What is a prerequisite?", options=["A needed foundation", "A reward"], answer="A needed foundation"),
        ])
        topic_id, advanced_id = topic.id, advanced.id
        resource_ids = [resource.id for resource in resources]
        quiz_id = quiz.id
        question_ids = [question.id for question in quiz.questions]
        answers = [question.answer for question in quiz.questions]
        db.session.commit()
        return {
            "topic_id": topic_id,
            "advanced_id": advanced_id,
            "resource_ids": resource_ids,
            "quiz_id": quiz_id,
            "question_ids": question_ids,
            "answers": answers,
        }


@pytest.fixture()
def user(app):
    with app.app_context():
        item = User(email="learner@example.test", name="Test Learner")
        item.set_password("correct horse")
        db.session.add(item)
        db.session.commit()
        return item.id


def login(client):
    return client.post("/login", data={"email": "learner@example.test", "password": "correct horse"})
