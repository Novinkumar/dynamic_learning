"""Create a deterministic, self-contained programming learning catalog."""
import sys
from sqlalchemy.engine import make_url

from app import create_app, db
from app.models import User, Topic, Resource, Quiz, Question, Prerequisite, QuizAttempt, utcnow_naive
from app.services.catalog import TOPICS, PREREQUISITES, RESOURCE_CATALOG
from app.services.question_bank import curated_bank
from config import DEMO_ACCOUNT_EMAIL


def seed(app=None, reset=False):
    app = app or create_app()
    with app.app_context():
        environment = str(app.config.get("APP_ENV", "")).strip().lower()
        if reset:
            # drop_all includes bound engines, so check every target before any drop.
            if (environment not in {"development", "test", "testing"}
                    or make_url(app.config["SQLALCHEMY_DATABASE_URI"]).get_backend_name() != "sqlite"
                    or any(engine.url.get_backend_name() != "sqlite" for engine in db.engines.values())):
                raise ValueError("Database reset is only allowed for development/test SQLite databases.")
            db.drop_all()
            db.create_all()
            from app.services.schema import ensure_schema
            ensure_schema()
        demo_enabled = environment != "production" and app.config.get("DEMO_ACCOUNT_ENABLED", False)
        if demo_enabled and not User.query.filter_by(email=DEMO_ACCOUNT_EMAIL).first():
            demo = User(email=DEMO_ACCOUNT_EMAIL, name="Demo Learner", is_admin=True)
            demo.set_password("password123")
            db.session.add(demo)
        topics = {name: Topic.query.filter_by(name=name).first() for name, _ in TOPICS}
        for name, description in TOPICS:
            if not topics[name]:
                topics[name] = Topic(name=name, description=description)
                db.session.add(topics[name])
        db.session.flush()
        for child, parent in PREREQUISITES:
            if not Prerequisite.query.filter_by(topic_id=topics[child].id, prerequisite_id=topics[parent].id).first():
                db.session.add(Prerequisite(topic_id=topics[child].id, prerequisite_id=topics[parent].id, minimum_mastery=.6))
        for name, _ in TOPICS:
            topic = topics[name]
            for label, details in zip(("beginner guide", "practice exercises", "challenge lab"), RESOURCE_CATALOG[name]):
                title = f"{name}: {label}"
                resource = Resource.query.filter_by(topic_id=topic.id, title=title).first()
                if resource is None:
                    resource = Resource(topic_id=topic.id, title=title)
                    db.session.add(resource)
                resource.url, resource.kind, resource.difficulty, resource.estimated_minutes, resource.description = details
            # Only shared catalog quizzes are updated here; never touch a
            # learner's generated practice session.
            quiz = Quiz.query.filter_by(topic_id=topic.id, title=f"{name} quick check", source="catalog").first()
            if quiz:
                placeholders = [question for question in quiz.questions if question.prompt == f"Which statement best describes {name} in Python?"]
                if placeholders and QuizAttempt.query.filter_by(quiz_id=quiz.id).first():
                    # Preserve historical question/answer records from the old demo quiz.
                    quiz.title = f"{name} legacy check"
                    quiz = None
                else:
                    for question in placeholders:
                        db.session.delete(question)
            if quiz is None:
                quiz = Quiz(topic_id=topic.id, title=f"{name} quick check", source="catalog")
                db.session.add(quiz)
                db.session.flush()
            quiz.source = "catalog"
            quiz.owner_id = None
            quiz.created_at = quiz.created_at or utcnow_naive()
            existing = {question.prompt: question for question in quiz.questions}
            for item in curated_bank(name):
                question = existing.get(item["prompt"])
                if question is None:
                    question = Question(quiz_id=quiz.id, prompt=item["prompt"], options=list(item["options"]),
                                        answer=item["answer"])
                    db.session.add(question)
                # Explanations were previously derived at runtime. Persisting
                # them also makes feedback available for every curated item.
                question.explanation = item["explanation"]
                question.skill = item["skill"]
                question.difficulty = item["difficulty"]
        db.session.commit()
        print(f"Seeded the seven-topic catalog; demo account {'enabled' if demo_enabled else 'disabled'}.")

if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
