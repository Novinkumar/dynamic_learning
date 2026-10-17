from datetime import timedelta

from ..models import QuizAttempt, Resource, ResourceCompletion, Topic, utcnow_naive
from .mastery import topic_mastery

MASTERY_THRESHOLD = 0.65
REVISION_DAYS = 14


def _mastery(user_id):
    return {topic.id: topic_mastery(user_id, topic.id) for topic in Topic.query.all()}


def _reasons(user_id, resource, mastery, completed):
    reasons = []
    topic_score = mastery.get(resource.topic_id, 0.0)
    attempts = (QuizAttempt.query.join(QuizAttempt.quiz)
                .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz.has(topic_id=resource.topic_id))
                .order_by(QuizAttempt.completed_at.desc()).all())
    if not attempts:
        reasons.append(f"Start with {resource.topic.name}: you have no quiz history yet")
    elif topic_score < MASTERY_THRESHOLD:
        reasons.append(f"Your current {resource.topic.name} mastery is {topic_score:.0%}")
        if attempts[0].score < 0.6:
            reasons.append(f"Your recent {resource.topic.name} quiz score was low ({attempts[0].score:.0%})")
        else:
            reasons.append(f"Your latest {resource.topic.name} quiz score was {attempts[0].score:.0%}; keep practising to build mastery")
    elif resource.difficulty >= 3:
        reasons.append(f"Your {resource.topic.name} mastery is strong, so advanced practice is appropriate")
    old = next((c for c in completed if c.resource_id == resource.id), None)
    if old and old.completed_at < utcnow_naive() - timedelta(days=REVISION_DAYS):
        reasons.append("It has been a while since you completed this resource; revision is due")
    for prereq in resource.topic.prerequisites:
        if mastery.get(prereq.prerequisite_id, 0.0) < prereq.minimum_mastery:
            reasons.append(f"Study {prereq.prerequisite.name} first because it is a prerequisite")
    return reasons or ["A suitable next step based on your learning path and current mastery"]


def recommend_resources(user_id, limit=5):
    """Rank resources with deterministic, explainable adaptive signals.

    Resource objects receive non-persistent ``reason`` and ``priority`` attributes
    for use by both JSON routes and Jinja templates.
    """
    mastery = _mastery(user_id)
    completed = ResourceCompletion.query.filter_by(user_id=user_id).all()
    cutoff = utcnow_naive() - timedelta(days=REVISION_DAYS)
    # A recent completion is suppressed; an old completion becomes eligible for revision.
    completed_ids = {c.resource_id for c in completed if c.completed_at >= cutoff}
    candidates = []
    for resource in Resource.query.all():
        if resource.id in completed_ids:
            continue
        topic_score = mastery.get(resource.topic_id, 0.0)
        score = 50.0 + (1.0 - topic_score) * 35 - resource.difficulty * 3
        for prereq in resource.topic.prerequisites:
            if mastery.get(prereq.prerequisite_id, 0.0) < prereq.minimum_mastery:
                score -= 20
        resource.priority = round(score, 2)
        resource.reason = "; ".join(_reasons(user_id, resource, mastery, completed))
        resource.explanation = resource.reason
        candidates.append(resource)
    candidates.sort(key=lambda r: (-r.priority, r.id))
    try:
        count = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        count = 5
    return candidates[:count]


def recommendation_plan(user_id, support_limit=2):
    """Return one primary next step and a small, non-redundant support set."""
    try:
        support_limit = max(0, min(int(support_limit), 4))
    except (TypeError, ValueError):
        support_limit = 2
    ranked = recommend_resources(user_id, max(5, support_limit + 3))
    if not ranked:
        return {"primary": None, "supporting": [], "all": []}
    primary = ranked[0]
    supporting = []
    seen_signals = {(primary.topic_id, primary.kind)}
    for resource in ranked[1:]:
        signal = (resource.topic_id, resource.kind)
        if resource.id == primary.id or signal in seen_signals:
            continue
        supporting.append(resource)
        seen_signals.add(signal)
        if len(supporting) >= support_limit:
            break
    # If a small catalog has no distinct topic/kind combinations, fill from
    # the ranked list while still never repeating a resource.
    if len(supporting) < support_limit:
        selected_ids = {primary.id, *(item.id for item in supporting)}
        for resource in ranked[1:]:
            if resource.id not in selected_ids:
                supporting.append(resource)
                selected_ids.add(resource.id)
            if len(supporting) >= support_limit:
                break
    return {"primary": primary, "supporting": supporting,
            "all": [primary, *supporting]}
