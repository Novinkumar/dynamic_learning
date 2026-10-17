from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


def utcnow_naive():
    """Return a UTC timestamp without tzinfo for the existing SQLite schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    completions = db.relationship("ResourceCompletion", back_populates="user", cascade="all, delete-orphan")
    mastery_scores = db.relationship("MasteryScore", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    resources = db.relationship("Resource", back_populates="topic", cascade="all, delete-orphan")
    quizzes = db.relationship("Quiz", back_populates="topic", cascade="all, delete-orphan")
    prerequisites = db.relationship("Prerequisite", foreign_keys="Prerequisite.topic_id", back_populates="topic", cascade="all, delete-orphan")


class Prerequisite(db.Model):
    __table_args__ = (db.UniqueConstraint("topic_id", "prerequisite_id", name="uq_topic_prerequisite"),)
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False, index=True)
    prerequisite_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False, index=True)
    minimum_mastery = db.Column(db.Float, default=0.6, nullable=False)
    topic = db.relationship("Topic", foreign_keys=[topic_id], back_populates="prerequisites")
    prerequisite = db.relationship("Topic", foreign_keys=[prerequisite_id])


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    kind = db.Column(db.String(50), default="article", nullable=False)
    difficulty = db.Column(db.Integer, default=2, nullable=False)
    estimated_minutes = db.Column(db.Integer, default=10, nullable=False)
    description = db.Column(db.Text, default="")
    topic = db.relationship("Topic", back_populates="resources")


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    topic = db.relationship("Topic", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    answer = db.Column(db.String(255), nullable=False)
    quiz = db.relationship("Quiz", back_populates="questions")
    responses = db.relationship("QuestionResponse", back_populates="question", cascade="all, delete-orphan")


class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    completed_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    user = db.relationship("User", back_populates="attempts")
    quiz = db.relationship("Quiz")
    responses = db.relationship("QuestionResponse", back_populates="attempt", cascade="all, delete-orphan")


class QuestionResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempt.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False, index=True)
    answer = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    attempt = db.relationship("QuizAttempt", back_populates="responses")
    question = db.relationship("Question", back_populates="responses")


class ResourceCompletion(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "resource_id", name="uq_completion_user_resource"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=False)
    completed_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    user = db.relationship("User", back_populates="completions")
    resource = db.relationship("Resource")


class ResourceInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=False, index=True)
    event = db.Column(db.String(30), nullable=False, default="view")
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)


class MasteryScore(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "topic_id", name="uq_mastery_user_topic"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False)
    score = db.Column(db.Float, default=0.0, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
    user = db.relationship("User", back_populates="mastery_scores")
    topic = db.relationship("Topic")
