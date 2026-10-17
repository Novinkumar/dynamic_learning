from .. import db
from ..models import MasteryScore, QuizAttempt, utcnow_naive


def update_mastery(user_id, topic_id, quiz_score, learning_rate=0.35, commit=True):
    """Refresh recorded evidence, or apply a synthetic/manual update without attempts."""
    recorded = _attempt_mastery(user_id, topic_id)
    score = MasteryScore.query.filter_by(user_id=user_id, topic_id=topic_id).first()
    if score is None:
        score = MasteryScore(user_id=user_id, topic_id=topic_id, score=0.0)
        db.session.add(score)
    if recorded is not None:
        score.score = recorded
    else:
        score.score = round(max(0.0, min(1.0, score.score + learning_rate * (quiz_score - score.score))), 4)
    score.updated_at = utcnow_naive()
    if commit:
        db.session.commit()
    return score


def _attempt_mastery(user_id, topic_id):
    """Replay authoritative quiz evidence in chronological, stable order."""
    attempts = (QuizAttempt.query.join(QuizAttempt.quiz)
                .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz.has(topic_id=topic_id))
                .order_by(QuizAttempt.completed_at, QuizAttempt.id).all())
    if attempts:
        estimate = 0.0
        for attempt in attempts:
            estimate = round(estimate + 0.35 * (attempt.score - estimate), 4)
        return estimate
    return None


def topic_mastery(user_id, topic_id):
    """Return the same evidence-based EMA used to refresh the mastery cache."""
    recorded = _attempt_mastery(user_id, topic_id)
    if recorded is not None:
        return recorded
    # A stored score can represent an imported/manual assessment. It is only
    # considered assessed when an explicit row exists; an absent row is a true
    # cold-start state, not a weak score of zero.
    stored = MasteryScore.query.filter_by(user_id=user_id, topic_id=topic_id).first()
    return stored.score if stored is not None else 0.0


def get_mastery(user_id, topic_id):
    return topic_mastery(user_id, topic_id)
