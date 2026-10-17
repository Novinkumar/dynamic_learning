from flask import Blueprint, abort, jsonify, request, render_template
from sqlalchemy import or_
from .common import current_user, login_required
from .. import db
from ..models import Quiz, QuizAttempt, Question, QuestionResponse, Resource, ResourceCompletion, ResourceInteraction, Topic
from ..services.catalog import question_explanation
from ..services.mastery import topic_mastery, update_mastery
from ..services.recommender import recommendation_plan, recommend_resources

learning_bp = Blueprint("learning", __name__)


def _get_or_404(model, object_id):
    item = db.session.get(model, object_id)
    if item is None:
        abort(404)
    return item


def _recommendation_payload(resource):
    return {"id": resource.id, "title": resource.title, "topic": resource.topic.name,
            "priority": resource.priority, "reason": resource.reason,
            "explanation": resource.reason}


def _plan_payload(plan):
    return {"primary": _recommendation_payload(plan["primary"]) if plan["primary"] else None,
            "supporting": [_recommendation_payload(item) for item in plan["supporting"]],
            "all": [_recommendation_payload(item) for item in plan["all"]]}


@learning_bp.get("/api/resources")
@login_required
def resources():
    query = request.args.get("q", "").strip().lower()
    topic_id = request.args.get("topic", type=int)
    kind = request.args.get("kind", "").strip()
    requested_limit = request.args.get("limit", 5)
    candidates = recommend_resources(current_user().id, 50 if query or topic_id or kind else requested_limit)
    if query:
        candidates = [item for item in candidates if query in item.title.lower() or query in item.topic.name.lower() or query in item.description.lower()]
    if topic_id:
        candidates = [item for item in candidates if item.topic_id == topic_id]
    if kind:
        candidates = [item for item in candidates if item.kind == kind]
    try:
        candidates = candidates[:max(1, min(int(requested_limit), 50))]
    except (TypeError, ValueError):
        candidates = candidates[:5]
    return jsonify(resources=[{"id": r.id, "title": r.title, "url": r.url, "topic": r.topic.name,
                              "topic_id": r.topic_id, "kind": r.kind, "description": r.description,
                              "difficulty": r.difficulty, "estimated_minutes": r.estimated_minutes,
                              "reason": r.reason, "explanation": r.reason, "priority": r.priority} for r in candidates])


@learning_bp.get("/library")
@login_required
def library():
    user = current_user()
    kind = request.args.get("kind", "").strip()
    query_text = request.args.get("q", "").strip()
    topic_id = request.args.get("topic", type=int)
    query = Resource.query
    if kind:
        query = query.filter_by(kind=kind)
    if topic_id:
        query = query.filter_by(topic_id=topic_id)
    if query_text:
        query = query.filter(or_(Resource.title.ilike(f"%{query_text}%"), Resource.description.ilike(f"%{query_text}%")))
    completed_resource_ids = {item.resource_id for item in
                              ResourceCompletion.query.filter_by(user_id=user.id).all()}
    return render_template("library.html", resources=query.order_by(Resource.id).all(),
                           topics=Topic.query.order_by(Topic.id).all(), selected_kind=kind,
                           query=query_text, user=user, completed_resource_ids=completed_resource_ids)


@learning_bp.get("/quiz/<int:quiz_id>")
@login_required
def quiz_page(quiz_id):
    item = _get_or_404(Quiz, quiz_id)
    return render_template("quiz.html", quiz=item)


@learning_bp.post("/api/resources/<int:resource_id>/complete")
@login_required
def complete(resource_id):
    resource = _get_or_404(Resource, resource_id)
    existing = ResourceCompletion.query.filter_by(user_id=current_user().id, resource_id=resource.id).first()
    if not existing:
        db.session.add(ResourceCompletion(user_id=current_user().id, resource_id=resource.id))
    db.session.add(ResourceInteraction(user_id=current_user().id, resource_id=resource.id, event="complete"))
    db.session.commit()
    return jsonify(ok=True, resource_id=resource.id)


@learning_bp.get("/api/quizzes/<int:quiz_id>")
@login_required
def quiz(quiz_id):
    item = _get_or_404(Quiz, quiz_id)
    return jsonify(id=item.id, title=item.title, topic=item.topic.name, topic_id=item.topic_id,
                   questions=[{"id": q.id, "prompt": q.prompt, "options": q.options} for q in item.questions],
                   resources=[{"id": resource.id, "title": resource.title, "url": resource.url,
                               "description": resource.description} for resource in item.topic.resources])


@learning_bp.post("/api/quizzes/<int:quiz_id>/submit")
@login_required
def submit_quiz(quiz_id):
    quiz = _get_or_404(Quiz, quiz_id)
    learner_id = current_user().id
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="request body must be a JSON object"), 400
    answers = data.get("answers", {})
    if not isinstance(answers, dict):
        return jsonify(error="answers must be an object"), 400
    if not quiz.questions:
        return jsonify(error="quiz has no questions"), 422
    questions = {str(question.id): question for question in quiz.questions}
    for question_id, answer in answers.items():
        if question_id not in questions:
            return jsonify(error="answers contain an unknown question id"), 400
        if not isinstance(answer, str) or answer not in questions[question_id].options:
            return jsonify(error="answers must be strings matching a question option"), 400
    graded_answers = [
        (question, answers.get(question_id, ""),
         question_id in answers and answers[question_id] == question.answer)
        for question_id, question in questions.items()
    ]
    previous_attempt = (QuizAttempt.query.join(QuizAttempt.quiz)
                        .filter(QuizAttempt.user_id == learner_id,
                                QuizAttempt.quiz.has(topic_id=quiz.topic_id))
                        .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc()).first())
    previous_mastery = round(topic_mastery(learner_id, quiz.topic_id), 4)
    previous_plan = recommendation_plan(learner_id, support_limit=2)
    # ORM resources are reused by SQLAlchemy; snapshot the pre-submit values
    # before the post-submit recommendation pass updates transient reasons.
    previous_snapshot = _plan_payload(previous_plan)
    correct = sum(is_correct for _, _, is_correct in graded_answers)
    score = correct / len(quiz.questions)
    attempt = QuizAttempt(user_id=learner_id, quiz_id=quiz.id, score=score, answers=answers)
    try:
        db.session.add(attempt)
        db.session.flush()
        for question, answer, is_correct in graded_answers:
            db.session.add(QuestionResponse(attempt_id=attempt.id, question_id=question.id,
                                            answer=answer, is_correct=is_correct))
        mastery = update_mastery(learner_id, quiz.topic_id, score, commit=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    feedback = []
    for question, answer, is_correct in graded_answers:
        feedback.append({"question_id": question.id, "prompt": question.prompt,
                         "correct": is_correct, "answer": answer,
                         "correct_answer": question.answer,
                         "explanation": question_explanation(question)})
    latest_mastery = round(topic_mastery(learner_id, quiz.topic_id), 4)
    next_plan = recommendation_plan(learner_id, support_limit=2)
    next_snapshot = _plan_payload(next_plan)
    before_ids = [item["id"] for item in previous_snapshot["all"]]
    after_ids = [item["id"] for item in next_snapshot["all"]]
    before_signature = [(item["id"], item["priority"], item["reason"]) for item in previous_snapshot["all"]]
    after_signature = [(item["id"], item["priority"], item["reason"]) for item in next_snapshot["all"]]
    before_primary = previous_snapshot["primary"]["id"] if previous_snapshot["primary"] else None
    after_primary = next_snapshot["primary"]["id"] if next_snapshot["primary"] else None
    adaptation = {
        "previous_score": round(previous_attempt.score, 4) if previous_attempt else None,
        "latest_score": round(score, 4),
        "score_change": round(score - previous_attempt.score, 4) if previous_attempt else None,
        "previous_mastery": previous_mastery,
        "latest_mastery": latest_mastery,
        "mastery_change": round(latest_mastery - previous_mastery, 4),
        "previous_primary": previous_snapshot["primary"],
        "next_primary": next_snapshot["primary"],
        "previous_next_steps": before_ids,
        "next_steps": after_ids,
        "recommendations_changed": before_signature != after_signature or before_primary != after_primary,
    }
    return jsonify(attempt_id=attempt.id, score=score, correct=correct, total=len(quiz.questions), mastery=mastery.score,
                    feedback=feedback,
                    recommendations=[_recommendation_payload(item) for item in next_plan["all"]],
                    primary_recommendation=_recommendation_payload(next_plan["primary"]) if next_plan["primary"] else None,
                    supporting_recommendations=[_recommendation_payload(item) for item in next_plan["supporting"]],
                    adaptation=adaptation)
