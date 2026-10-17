from types import SimpleNamespace

from flask import Blueprint, jsonify, render_template
from .common import current_user, login_required
from ..models import Topic, Quiz, QuizAttempt, Resource, ResourceCompletion
from ..services.catalog import TOPICS
from ..services.metrics import learning_summary
from ..services.recommender import recommendation_plan

dashboard_bp = Blueprint("dashboard", __name__)


def _resource_payload(resource):
    if resource is None:
        return None
    return {"id": resource.id, "title": resource.title, "url": resource.url,
            "topic": resource.topic.name, "kind": resource.kind,
            "description": resource.description, "difficulty": resource.difficulty,
            "estimated_minutes": resource.estimated_minutes,
            "reason": getattr(resource, "reason", ""),
            "explanation": getattr(resource, "reason", ""),
            "priority": getattr(resource, "priority", 0.0)}


@dashboard_bp.get("/")
def home():
    if not current_user():
        return jsonify(message="Dynamic Learning Resource Recommender", login="/login")
    return dashboard()


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    plan = recommendation_plan(user.id, support_limit=2)
    recs = plan["all"]
    summary = learning_summary(user.id)
    topics = Topic.query.order_by(Topic.id).all()
    # A new app may be opened before seed.py has been run.  The UI can still
    # explain the intended Python path and gracefully show unavailable checks.
    display_topics = topics or [SimpleNamespace(id=-(index + 1), name=name, description=description, quizzes=[])
                                for index, (name, description) in enumerate(TOPICS)]
    attempts = (QuizAttempt.query.filter_by(user_id=user.id)
                .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc()).all())
    payload = {"user": user, "recommendations": recs,
               "primary_recommendation": plan["primary"],
               "supporting_recommendations": plan["supporting"], **summary,
               "topics": display_topics, "topic_list": display_topics,
               "quizzes": Quiz.query.order_by(Quiz.id).all(),
               "quiz_history": attempts, "attempts": attempts,
               "resource_count": summary["progress"]["resources_total"],
               "attempt_count": QuizAttempt.query.filter_by(user_id=user.id).count(),
               "completion_count": ResourceCompletion.query.filter_by(user_id=user.id).count(),
               "mastery": summary["mastery"]}
    try:
        return render_template("dashboard.html", **payload)
    except Exception:
        return jsonify(payload)


@dashboard_bp.get("/api/dashboard")
@login_required
def dashboard_api():
    user = current_user()
    plan = recommendation_plan(user.id, support_limit=2)
    summary = learning_summary(user.id)
    return jsonify(user={"id": user.id, "name": user.name, "email": user.email},
                   recommendations=[_resource_payload(r) for r in plan["all"]],
                   primary_recommendation=_resource_payload(plan["primary"]),
                   supporting_recommendations=[_resource_payload(r) for r in plan["supporting"]],
                   **summary)


@dashboard_bp.get("/api/progress")
@login_required
def progress_api():
    """Return progress, weak topics, scores, history, and the current queue."""
    user = current_user()
    summary = learning_summary(user.id)
    plan = recommendation_plan(user.id, support_limit=2)
    summary["recommendations"] = [
        _resource_payload(item) for item in plan["all"]
    ]
    summary["primary_recommendation"] = _resource_payload(plan["primary"])
    summary["supporting_recommendations"] = [_resource_payload(item) for item in plan["supporting"]]
    return jsonify(**summary)


@dashboard_bp.get("/api/quiz-history")
@login_required
def quiz_history_api():
    history = learning_summary(current_user().id)["quiz_history"]
    return jsonify(history=history, attempts=history)


@dashboard_bp.get("/api/topic-mastery")
@login_required
def topic_mastery_api():
    topics = learning_summary(current_user().id)["topic_mastery"]
    return jsonify(topics=topics, mastery=topics)
