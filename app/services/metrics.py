from ..models import MasteryScore, QuizAttempt, Resource, ResourceCompletion, Topic
from .mastery import topic_mastery
from .offline_evaluation import ranking_metrics

MASTERY_THRESHOLD = 0.65


def precision_at_k(recommended, relevant, k=5):
    return ranking_metrics(recommended, relevant, k)["precision_at_k"]


def recall_at_k(recommended, relevant, k=5):
    return ranking_metrics(recommended, relevant, k)["recall_at_k"]


def ndcg_at_k(recommended, relevant, k=5):
    return ranking_metrics(recommended, relevant, k)["ndcg_at_k"]


def evaluation_metrics():
    attempts = QuizAttempt.query.all()
    completions = ResourceCompletion.query.all()
    if not attempts and not completions:
        # Keep the compact cold-start contract stable; the evaluation page can
        # explain that ranking metrics are unavailable until labels exist.
        return {"attempts": 0, "mean_score": 0.0, "completion_rate": 0.0}
    completed_resource_ids = {item.resource_id for item in completions}
    resource_count = Resource.query.count()
    return {"attempts": len(attempts), "mean_score": round(sum(a.score for a in attempts) / len(attempts), 4) if attempts else 0.0,
            "completion_rate": round(len(completed_resource_ids) / resource_count, 4) if resource_count else 0.0,
            "completed_resources": len(completed_resource_ids),
            "resource_catalog_size": resource_count,
            "completion_definition": "Unique catalog resources completed at least once / catalog resource count.",
            "precision_at_5": None, "recall_at_5": None, "ndcg_at_5": None,
             "assumption": "Ranking metrics require held-out relevance labels; descriptive data is shown instead."}


def _attempt_payload(attempt):
    responses = list(attempt.responses)
    correct = sum(response.is_correct for response in responses)
    total = len(responses) or len(attempt.quiz.questions)
    return {
        "id": attempt.id,
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "quiz": attempt.quiz.title,
        "title": attempt.quiz.title,
        "topic_id": attempt.quiz.topic_id,
        "topic": attempt.quiz.topic.name,
        "score": round(attempt.score, 4),
        "correct": correct,
        "total": total,
        "completed_at": attempt.completed_at.isoformat(),
        "responses": [
            {"question_id": response.question_id, "answer": response.answer,
             "is_correct": response.is_correct}
            for response in responses
        ],
    }


def learning_summary(user_id):
    """Build the learner-facing progress contract from persisted activity."""
    topics = Topic.query.order_by(Topic.id).all()
    attempts = (QuizAttempt.query.filter_by(user_id=user_id)
                .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc()).all())
    completions = ResourceCompletion.query.filter_by(user_id=user_id).all()
    attempt_topic_ids = {attempt.quiz.topic_id for attempt in attempts}
    stored_topic_ids = {row.topic_id for row in MasteryScore.query.filter_by(user_id=user_id).all()}
    assessed_topic_ids = attempt_topic_ids | stored_topic_ids
    mastery = {topic.id: round(topic_mastery(user_id, topic.id), 4) for topic in topics}
    assessed_mastery = {topic_id: mastery[topic_id] for topic_id in assessed_topic_ids if topic_id in mastery}
    weak_topics = [
        {"topic_id": topic.id, "topic": topic.name, "mastery": mastery[topic.id],
         "description": topic.description,
         "reason": "Needs more practice"}
        for topic in sorted(topics, key=lambda item: (mastery[item.id], item.id))
        if topic.id in assessed_topic_ids and mastery[topic.id] < MASTERY_THRESHOLD
    ]
    quiz_scores = [_attempt_payload(attempt) for attempt in attempts]
    average = round(sum(attempt.score for attempt in attempts) / len(attempts), 4) if attempts else 0.0
    resource_ids = {completion.resource_id for completion in completions}
    total_resources = Resource.query.count()
    overall_progress = round(len(resource_ids) / total_resources, 4) if total_resources else 0.0
    overall_mastery = (round(sum(assessed_mastery.values()) / len(assessed_mastery), 4)
                       if assessed_mastery else 0.0)
    return {
        "progress": {
            "resources_completed": len(resource_ids),
            "resources_total": total_resources,
            "quizzes_completed": len(attempts),
            "topics_started": len(assessed_topic_ids),
            "topics_total": len(topics),
            "topics_mastered": sum(value >= MASTERY_THRESHOLD for value in assessed_mastery.values()),
            "assessed_topics": len(assessed_topic_ids),
            "unassessed_topics": max(0, len(topics) - len(assessed_topic_ids)),
            "overall_mastery": overall_mastery,
            "average_quiz_score": average,
        },
        "overall_progress": overall_progress,
        "completed_resource_ids": sorted(resource_ids),
        # Only assessed topics appear in this mapping. Templates can therefore
        # distinguish "not assessed" from a measured weak score of 0%.
        "mastery": assessed_mastery,
        "quiz_scores": quiz_scores,
        "scores": quiz_scores,
        "quiz_history": quiz_scores,
        "topic_mastery": [
            {"topic_id": topic.id, "topic": topic.name, "mastery": mastery[topic.id],
             "assessed": topic.id in assessed_topic_ids,
             "description": topic.description,
             "prerequisites": [
                 {"topic_id": prerequisite.prerequisite_id,
                  "topic": prerequisite.prerequisite.name,
                  "minimum_mastery": prerequisite.minimum_mastery}
                 for prerequisite in topic.prerequisites
             ]}
             for topic in topics
        ],
        "weak_topics": weak_topics,
    }
