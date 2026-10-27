from flask import (
    Blueprint, abort, current_app, flash, jsonify, make_response, redirect,
    render_template, request, url_for,
)
from sqlalchemy import or_
from .common import current_user, login_required
from .. import db
from ..models import (
    Quiz, QuizAttempt, Question, QuestionResponse, Resource,
    ResourceCompletion, ResourceInteraction, Topic, utcnow_naive,
)
from ..services.catalog import question_explanation
from ..services.mastery import topic_mastery, update_mastery
from ..services.metrics import learning_summary
from ..services.question_bank import resolve_topic
from ..services.quiz_ai import (
    choose_difficulty, difficulty_reason, generate_quiz, provider_status,
)
from ..services.recommender import recommendation_plan, recommend_resources

learning_bp = Blueprint("learning", __name__)

DIFFICULTY_CHOICES = (
    ("adaptive", "Adaptive to my mastery"),
    ("foundation", "Foundation · build confidence"),
    ("core", "Core · balanced practice"),
    ("stretch", "Stretch · challenge me"),
)


def _get_or_404(model, object_id):
    item = db.session.get(model, object_id)
    if item is None:
        abort(404)
    return item


def _get_quiz_for_user(quiz_id):
    """Shared catalog quizzes are public; generated sessions are private."""
    item = _get_or_404(Quiz, quiz_id)
    if item.source == "generated" and item.owner_id != current_user().id:
        abort(404)
    return item


def _recommendation_payload(resource):
    return {"id": resource.id, "title": resource.title, "url": resource.url,
            "topic": resource.topic.name, "kind": resource.kind,
            "difficulty": resource.difficulty,
            "estimated_minutes": resource.estimated_minutes,
            "priority": resource.priority, "reason": resource.reason,
            "explanation": resource.reason}


def _plan_payload(plan):
    return {"primary": _recommendation_payload(plan["primary"]) if plan["primary"] else None,
            "supporting": [_recommendation_payload(item) for item in plan["supporting"]],
            "all": [_recommendation_payload(item) for item in plan["all"]]}


def _provider_label(provider, model=""):
    if provider == "live_ai":
        return f"Live AI · {model}" if model else "Live AI"
    if provider == "offline_fallback":
        return "Offline AI · fallback"
    if provider == "offline_generator":
        return "Offline AI generator"
    return "Classic quick check"


def _length_choices(config):
    default = config.get("AI_QUIZ_DEFAULT_LENGTH", 10)
    maximum = config.get("AI_QUIZ_MAX_LENGTH", 20)
    try:
        default, maximum = int(default), int(maximum)
    except (TypeError, ValueError):
        default, maximum = 10, 20
    maximum = max(default, min(20, maximum))
    return sorted({value for value in (8, 10, 12, 15, 20, default, maximum)
                   if 5 <= value <= maximum})


def _practice_topic_stats(user_id, topics):
    """Assemble only real, stored evidence for the AI practice selector."""
    summary = learning_summary(user_id)
    assessed = set(summary["mastery"])
    latest_scores = {}
    for item in summary["quiz_history"]:
        latest_scores.setdefault(item["topic_id"], item["score"])
    stats = []
    for topic in topics:
        mastery = summary["mastery"].get(topic.id, 0.0)
        stats.append({
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "mastery": mastery,
            "assessed": topic.id in assessed,
            "latest_score": latest_scores.get(topic.id),
            "suggested_difficulty": choose_difficulty(mastery, "adaptive"),
            "difficulty_reason": difficulty_reason(mastery, "adaptive", choose_difficulty(mastery, "adaptive")),
            "offline_supported": resolve_topic(topic.name) is not None,
        })
    return stats


def _recent_prompts(user_id, topic_id, limit=60):
    """Recent prompts are excluded so the next session feels genuinely fresh."""
    attempts = (QuizAttempt.query.join(QuizAttempt.quiz)
                .filter(QuizAttempt.user_id == user_id, Quiz.topic_id == topic_id)
                .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
                .limit(6).all())
    prompts = []
    seen = set()
    for attempt in attempts:
        for question in attempt.quiz.questions:
            key = " ".join(question.prompt.lower().split())
            if key not in seen:
                seen.add(key)
                prompts.append(question.prompt)
    return prompts[:limit]


def _recent_sessions(user_id, limit=6):
    quizzes = (Quiz.query.filter_by(source="generated", owner_id=user_id)
               .order_by(Quiz.created_at.desc(), Quiz.id.desc()).limit(limit).all())
    sessions = []
    for quiz in quizzes:
        attempt = (QuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz.id)
                   .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc()).first())
        sessions.append({
            "id": quiz.id,
            "title": quiz.title,
            "topic": quiz.topic.name,
            "topic_id": quiz.topic_id,
            "question_count": len(quiz.questions),
            "mode": quiz.generation_mode or "core",
            "provider": _provider_label(quiz.generation_provider, quiz.generation_model),
            "created_at": quiz.created_at,
            "completed_at": quiz.completed_at,
            "score": attempt.score if attempt else None,
        })
    return sessions


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


@learning_bp.get("/practice")
@login_required
def practice_studio():
    """AI practice studio: choose a topic, length, and difficulty."""
    user = current_user()
    topics = _practice_topic_stats(user.id, Topic.query.order_by(Topic.id).all())
    selected = request.args.get("topic", type=int)
    valid_ids = {item["id"] for item in topics}
    if selected not in valid_ids:
        selected = next((item["id"] for item in topics if item["offline_supported"]), None)
    lengths = _length_choices(current_app.config)
    default_length = min(current_app.config.get("AI_QUIZ_DEFAULT_LENGTH", 10), lengths[-1] if lengths else 10)
    return render_template(
        "practice.html",
        topics=topics,
        selected_topic_id=selected,
        lengths=lengths,
        default_length=default_length,
        difficulties=DIFFICULTY_CHOICES,
        provider=provider_status(current_app.config),
        sessions=_recent_sessions(user.id),
        user=user,
    )


@learning_bp.post("/practice/generate")
@login_required
def generate_practice():
    """Create one fresh, private quiz session and redirect to its page."""
    user = current_user()
    topic_id = request.form.get("topic_id", type=int)
    topic = _get_or_404(Topic, topic_id) if topic_id else None
    if topic is None:
        return redirect(url_for("learning.practice_studio"))
    lengths = _length_choices(current_app.config)
    requested_length = request.form.get("length", type=int) or current_app.config.get("AI_QUIZ_DEFAULT_LENGTH", 10)
    length = min(max(requested_length, min(lengths)), max(lengths))
    difficulty = request.form.get("difficulty", "adaptive").strip()
    if difficulty not in {key for key, _ in DIFFICULTY_CHOICES}:
        difficulty = "adaptive"
    summary = learning_summary(user.id)
    mastery = summary["mastery"].get(topic.id, 0.0)
    latest = next((item["score"] for item in summary["quiz_history"]
                   if item["topic_id"] == topic.id), None)
    recent_prompts = _recent_prompts(user.id, topic.id)
    try:
        result = generate_quiz(
            current_app.config, topic.name, count=length, difficulty=difficulty,
            mastery=mastery, recent_score=latest, recent_prompts=recent_prompts,
        )
    except ValueError as exc:
        flash(str(exc) or "Could not generate a quiz for this topic. Choose a Python topic or configure live AI.", "error")
        return redirect(url_for("learning.practice_studio", topic=topic.id))
    quiz = Quiz(
        topic_id=topic.id,
        title=f"{topic.name} · fresh AI practice",
        source="generated",
        owner_id=user.id,
        generation_provider=result.provider,
        generation_model=result.model,
        generation_seed=result.seed,
        generation_mode=result.effective_difficulty,
        difficulty=result.requested_difficulty,
        created_at=utcnow_naive(),
    )
    db.session.add(quiz)
    db.session.flush()
    for item in result.questions:
        db.session.add(Question(
            quiz_id=quiz.id,
            prompt=item["prompt"],
            options=list(item["options"]),
            answer=item["answer"],
            explanation=item["explanation"],
            skill=item["skill"],
            difficulty=item["difficulty"],
        ))
    db.session.commit()
    if result.warning:
        flash(result.warning, "warning")
    else:
        flash(f"{length} fresh questions are ready. {result.label} · {result.effective_difficulty} level.", "success")
    return redirect(url_for("learning.quiz_page", quiz_id=quiz.id), code=303)


@learning_bp.get("/quiz/<int:quiz_id>")
@login_required
def quiz_page(quiz_id):
    item = _get_quiz_for_user(quiz_id)
    attempt = None
    if item.source == "generated" and item.completed_at:
        attempt = (QuizAttempt.query.filter_by(user_id=current_user().id, quiz_id=item.id)
                   .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc()).first())
    response = make_response(render_template(
        "quiz.html",
        quiz=item,
        attempt=attempt,
        provider_label=_provider_label(item.generation_provider, item.generation_model),
        practice_url=url_for("learning.practice_studio", topic=item.topic_id),
    ))
    response.headers["Cache-Control"] = "no-store"
    return response


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
    item = _get_quiz_for_user(quiz_id)
    response = jsonify(
        id=item.id, title=item.title, topic=item.topic.name, topic_id=item.topic_id,
        source=item.source,
        provider=_provider_label(item.generation_provider, item.generation_model),
        difficulty=item.generation_mode,
        question_count=len(item.questions),
        one_time=item.source == "generated",
        questions=[{"id": q.id, "prompt": q.prompt, "options": q.options,
                    "skill": q.skill, "difficulty": q.difficulty} for q in item.questions],
        resources=[{"id": resource.id, "title": resource.title, "url": resource.url,
                    "description": resource.description} for resource in item.topic.resources],
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@learning_bp.post("/api/quizzes/<int:quiz_id>/submit")
@login_required
def submit_quiz(quiz_id):
    quiz = _get_quiz_for_user(quiz_id)
    learner_id = current_user().id
    if quiz.source == "generated" and quiz.completed_at:
        return jsonify(error="This AI practice quiz has already been submitted. Generate a fresh quiz."), 409
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
        if quiz.source == "generated":
            quiz.completed_at = utcnow_naive()
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
                         "explanation": question_explanation(question),
                         "skill": question.skill, "difficulty": question.difficulty})
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
    response = jsonify(
        attempt_id=attempt.id, score=score, correct=correct, total=len(quiz.questions),
        mastery=mastery.score, feedback=feedback,
        source=quiz.source,
        provider=_provider_label(quiz.generation_provider, quiz.generation_model),
        practice_url=url_for("learning.practice_studio", topic=quiz.topic_id),
        recommendations=[_recommendation_payload(item) for item in next_plan["all"]],
        primary_recommendation=_recommendation_payload(next_plan["primary"]) if next_plan["primary"] else None,
        supporting_recommendations=[_recommendation_payload(item) for item in next_plan["supporting"]],
        adaptation=adaptation,
    )
    response.headers["Cache-Control"] = "no-store"
    return response
