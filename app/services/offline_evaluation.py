"""Read-only, reproducible offline ranking evaluation.

Call ``run_offline_evaluation()`` in an application context to snapshot the
existing catalog and evaluate an explicitly SYNTHETIC test dataset. Supplying
an ``EvaluationDataset(source="real", ...)`` requires independently supplied
held-out labels; this module never turns observed training activity into labels.
No users, interactions, mastery estimates, or recommendations are persisted.

The offline adaptive scorer replays the application's EMA and priority formula,
using each case's fixed split time instead of the wall clock. It evaluates
ranking behavior, not the live recommender's database cost or learning outcomes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from time import perf_counter

from sqlalchemy.orm import selectinload

from ..models import Resource, Topic
from .baseline import baseline_resources


SYNTHETIC_SPLIT_AT = datetime(2026, 1, 15, 12)


@dataclass(frozen=True)
class CatalogResource:
    id: int
    topic_id: int
    difficulty: int
    topic_name: str = ""
    prerequisites: tuple = ()  # (topic_id, minimum_mastery) pairs


@dataclass(frozen=True)
class Interaction:
    event: str  # quiz, complete, or view
    occurred_at: datetime  # naive UTC, matching the application's timestamps
    topic_id: int = None
    resource_id: int = None
    score: float = None


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    split_at: datetime
    interactions: tuple = ()
    relevant_resource_ids: tuple = None  # None/empty means no relevance labels
    scenario: str = ""
    label_rule: str = ""
    target_topic_id: int = None
    target_difficulty: int = None


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    source: str  # synthetic or real; provenance is explicitly caller-declared
    cases: tuple
    assumptions: tuple = ()
    scenario_label_rules: tuple = ()


def load_catalog():
    """Snapshot only catalog metadata, without reading actual learner activity."""
    resources = (Resource.query.options(
        selectinload(Resource.topic).selectinload(Topic.prerequisites)
    ).order_by(Resource.id).all())
    return tuple(CatalogResource(
        id=resource.id, topic_id=resource.topic_id, difficulty=resource.difficulty,
        topic_name=resource.topic.name,
        prerequisites=tuple(sorted(
            (link.prerequisite_id, link.minimum_mastery)
            for link in resource.topic.prerequisites
        )),
    ) for resource in resources)


def build_synthetic_dataset(catalog):
    """Build four deterministic, independently authored synthetic scenarios.

    Scenario labels are authored from each scenario's stated learning intent,
    before any ranker is called. They deliberately use different rules instead
    of treating the two easiest resources as universally relevant:

    * ``beginner_cold_start`` labels the target topic's minimum-difficulty
      introductory resource(s).
    * ``struggling_with_topic`` labels foundation and guided-practice material
      at the first two difficulty levels.
    * ``ready_for_advanced_material`` labels only the target topic's most
      difficult challenge resource(s).
    * ``revision_due`` labels a previously completed, now revision-due resource
      whose completion is outside the recent-completion suppression window.

    The rules are constructed test intentions, not measured relevance. The
    content baseline receives the target topic and suitable difficulty as
    explicit case metadata; it never derives labels from its own ranking.
    """
    by_topic = {}
    for resource in sorted(catalog, key=lambda item: item.id):
        by_topic.setdefault(resource.topic_id, []).append(resource)
    if not by_topic:
        return EvaluationDataset(
            "synthetic-learning-scenarios-v2", "synthetic", (),
            scenario_label_rules=_synthetic_scenario_rules(),
        )

    topic_ids = sorted(by_topic)

    def target_topic(index):
        # Repeating the deterministic topic sequence keeps all four scenarios
        # available even for a small caller-supplied catalog.
        return topic_ids[index % len(topic_ids)]

    def topic_resources(topic_id):
        return tuple(sorted(by_topic[topic_id], key=lambda item: (item.difficulty, item.id)))

    def labels_at_minimum(resources):
        minimum = min(resource.difficulty for resource in resources)
        return tuple(resource.id for resource in resources if resource.difficulty == minimum)

    def labels_at_foundation_and_practice(resources):
        minimum = min(resource.difficulty for resource in resources)
        return tuple(resource.id for resource in resources if resource.difficulty <= minimum + 1)

    def labels_at_maximum(resources):
        maximum = max(resource.difficulty for resource in resources)
        return tuple(resource.id for resource in resources if resource.difficulty == maximum)

    rules = dict(_synthetic_scenario_rules())
    cases = []

    beginner_topic = target_topic(0)
    beginner_resources = topic_resources(beginner_topic)
    beginner_labels = labels_at_minimum(beginner_resources)
    beginner_difficulty = min(resource.difficulty for resource in beginner_resources)
    cases.append(EvaluationCase(
        "beginner-cold-start", SYNTHETIC_SPLIT_AT,
        relevant_resource_ids=beginner_labels,
        scenario="beginner_cold_start", label_rule=rules["beginner_cold_start"],
        target_topic_id=beginner_topic, target_difficulty=beginner_difficulty,
    ))

    struggling_topic = target_topic(1)
    struggling_resources = topic_resources(struggling_topic)
    struggling_labels = labels_at_foundation_and_practice(struggling_resources)
    struggling_difficulty = min(
        resource.difficulty for resource in struggling_resources
        if resource.id in struggling_labels
    )
    struggling_history = tuple(
        Interaction("quiz", SYNTHETIC_SPLIT_AT - timedelta(days=2 - index),
                    topic_id=struggling_topic, score=score)
        for index, score in enumerate((0.15, 0.25))
    )
    cases.append(EvaluationCase(
        "struggling-with-topic", SYNTHETIC_SPLIT_AT, struggling_history,
        struggling_labels, "struggling_with_topic", rules["struggling_with_topic"],
        struggling_topic, struggling_difficulty,
    ))

    advanced_topic = target_topic(2)
    advanced_resources = topic_resources(advanced_topic)
    advanced_labels = labels_at_maximum(advanced_resources)
    advanced_difficulty = max(resource.difficulty for resource in advanced_resources)
    advanced_history = [
        Interaction("quiz", SYNTHETIC_SPLIT_AT - timedelta(days=4 - index),
                    topic_id=advanced_topic, score=score)
        for index, score in enumerate((0.9, 0.95))
    ]
    prerequisite_topics = sorted({topic_id for resource in advanced_resources
                                  for topic_id, _ in resource.prerequisites})
    for prerequisite_topic in prerequisite_topics:
        advanced_history.append(Interaction(
            "quiz", SYNTHETIC_SPLIT_AT - timedelta(days=7),
            topic_id=prerequisite_topic, score=0.9,
        ))
    cases.append(EvaluationCase(
        "ready-for-advanced-material", SYNTHETIC_SPLIT_AT,
        tuple(sorted(advanced_history, key=lambda item: item.occurred_at)),
        advanced_labels, "ready_for_advanced_material", rules["ready_for_advanced_material"],
        advanced_topic, advanced_difficulty,
    ))

    revision_topic = target_topic(3)
    revision_resources = topic_resources(revision_topic)
    # The middle item is a practice/revision resource in the seeded catalog;
    # use the final available item for a one-resource catalog.
    revision_resource = revision_resources[min(1, len(revision_resources) - 1)]
    revision_labels = (revision_resource.id,)
    revision_history = (
        Interaction("complete", SYNTHETIC_SPLIT_AT - timedelta(days=21),
                    resource_id=revision_resource.id),
        Interaction("view", SYNTHETIC_SPLIT_AT - timedelta(days=20),
                    resource_id=revision_resource.id),
    )
    cases.append(EvaluationCase(
        "revision-due", SYNTHETIC_SPLIT_AT, revision_history, revision_labels,
        "revision_due", rules["revision_due"], revision_topic, revision_resource.difficulty,
    ))

    return EvaluationDataset(
        "synthetic-learning-scenarios-v2", "synthetic", tuple(cases),
        tuple(rules.values()) + (
            "Target topic and difficulty metadata are authored jointly with the scenario label rules, "
            "not collected independently from learners. They are provided to the content baseline.",
            "Output-independent labels are not independent human judgments: the synthetic relevance rules "
            "and content baseline both use target topic and difficulty. The content baseline receives "
            "explicit intent metadata that adaptive and stable rankers do not consume; this comparison "
            "does not hold input information constant and can favor the content baseline.",
            "There is only one case per scenario. Target topic follows catalog ID order, so scenario and "
            "topic are confounded. No significance, learning-gain, or population claim is supported.",
            "The advanced-ready scenario name expresses author intent, not verified readiness: its two "
            "scores 0.9 and 0.95 yield EMA 0.5373, below the application's 0.65 threshold; prerequisite "
            "scores of 0.9 yield 0.315, below 0.6. Revision labels reflect a time policy, not evidence of forgetting.",
            "Constructed histories may favor or disadvantage individual rankers; synthetic "
            "results are not evidence of real-user uplift, retention, or learning outcomes.",
        ),
        tuple(rules.items()),
    )


def _synthetic_scenario_rules():
    """Return stable, human-readable label rules for the default scenarios."""
    return (
        (
            "beginner_cold_start",
            "beginner_cold_start: label every resource at the target topic's minimum "
            "catalog difficulty as introductory material.",
        ),
        (
            "struggling_with_topic",
            "struggling_with_topic: label target-topic resources at the minimum difficulty "
            "or one level above it as foundation and guided practice.",
        ),
        (
            "ready_for_advanced_material",
            "ready_for_advanced_material: label only the target topic's maximum-difficulty "
            "resource(s) as challenge material.",
        ),
        (
            "revision_due",
            "revision_due: label the target-topic resource completed 21 days earlier, "
            "because it is outside the 14-day recent-completion suppression window.",
        ),
    )


def _validate_k(k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")


def ranking_metrics(recommended, relevant, k=5):
    """Binary Precision@K, Recall@K, and NDCG@K, or None without labels.

    Precision uses K as its denominator even for a short recommendation list.
    Empty labels are unavailable evidence, not an assertion of zero relevance.
    """
    _validate_k(k)
    shown = list(recommended)[:k]
    if len(set(shown)) != len(shown):
        raise ValueError("recommendations must contain unique resource IDs")
    labels = set(relevant) if relevant is not None else set()
    if not labels:
        return {"precision_at_k": None, "recall_at_k": None, "ndcg_at_k": None}
    hits = sum(resource_id in labels for resource_id in shown)
    dcg = sum(1 / math.log2(rank + 2) for rank, resource_id in enumerate(shown)
              if resource_id in labels)
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(labels))))
    return {"precision_at_k": hits / k, "recall_at_k": hits / len(labels),
            "ndcg_at_k": dcg / ideal}


def _history_before_split(case):
    # Original input order is the deterministic tie-break for simultaneous events.
    return sorted((item for item in case.interactions if item.occurred_at < case.split_at),
                  key=lambda item: item.occurred_at)


def _candidates(catalog, history, split_at):
    cutoff = split_at - timedelta(days=14)
    completed = {item.resource_id for item in history
                 if item.event == "complete" and item.occurred_at >= cutoff}
    return tuple(resource for resource in catalog if resource.id not in completed)


def adaptive_resources(candidates, history, k=5):
    """Offline counterpart of the existing recommender's numerical scoring rules."""
    mastery = {}
    for item in history:
        if item.event == "quiz":
            old = mastery.get(item.topic_id, 0.0)
            mastery[item.topic_id] = round(old + 0.35 * (item.score - old), 4)

    def priority(resource):
        score = 50.0 + (1.0 - mastery.get(resource.topic_id, 0.0)) * 35 - resource.difficulty * 3
        score -= 20 * sum(mastery.get(topic_id, 0.0) < minimum
                          for topic_id, minimum in resource.prerequisites)
        return round(score, 2)

    return sorted(candidates, key=lambda resource: (-priority(resource), resource.id))[:k]


def content_based_resources(candidates, target_topic_id=None, target_difficulty=None, k=5,
                            *, topic_id=None, difficulty=None):
    """Rank by explicit topic relevance and proximity to a suitable difficulty.

    This intentionally small baseline uses only catalog metadata plus the
    scenario's explicit content preferences. A topic match always outranks a
    non-match; within each group, resources closest to the requested difficulty
    are preferred and IDs provide a stable final tie-break. ``topic_id`` and
    ``difficulty`` are accepted as readable aliases for callers constructing a
    baseline directly.
    """
    if target_topic_id is None:
        target_topic_id = topic_id
    if target_difficulty is None:
        target_difficulty = difficulty
    _validate_k(k)

    def sort_key(resource):
        topic_mismatch = 0 if target_topic_id is None or resource.topic_id == target_topic_id else 1
        if target_difficulty is None:
            difficulty_distance = 0
        else:
            difficulty_distance = abs(resource.difficulty - target_difficulty)
        return topic_mismatch, difficulty_distance, resource.difficulty, resource.id

    return sorted(candidates, key=sort_key)[:k]


def _validate_inputs(catalog, dataset):
    if dataset.source not in {"synthetic", "real"}:
        raise ValueError("dataset source must explicitly be synthetic or real")
    resource_ids = {resource.id for resource in catalog}
    if len(resource_ids) != len(catalog):
        raise ValueError("catalog must contain unique resource IDs")
    topic_ids = {resource.topic_id for resource in catalog}
    topic_ids.update(topic_id for resource in catalog for topic_id, _ in resource.prerequisites)
    if len({case.case_id for case in dataset.cases}) != len(dataset.cases):
        raise ValueError("dataset must contain unique case IDs")
    for case in dataset.cases:
        if case.split_at.tzinfo is not None:
            raise ValueError("split timestamps must be naive UTC")
        if case.target_topic_id is not None and case.target_topic_id not in topic_ids:
            raise ValueError("scenario target topic must identify a catalog topic")
        if (case.target_difficulty is not None
                and (isinstance(case.target_difficulty, bool)
                     or not isinstance(case.target_difficulty, (int, float))
                     or not math.isfinite(case.target_difficulty))):
            raise ValueError("scenario target difficulty must be a finite number")
        if not set(case.relevant_resource_ids or ()).issubset(resource_ids):
            raise ValueError("relevance labels must identify existing catalog resources")
        for item in case.interactions:
            if item.occurred_at.tzinfo is not None:
                raise ValueError("interaction timestamps must be naive UTC")
            if item.event == "quiz":
                if (item.topic_id not in topic_ids or item.score is None
                        or not math.isfinite(item.score) or not 0 <= item.score <= 1):
                    raise ValueError("quiz interactions require a catalog topic and a score in [0, 1]")
            elif item.event in {"complete", "view"}:
                if item.resource_id not in resource_ids:
                    raise ValueError("resource interactions must identify existing catalog resources")
            else:
                raise ValueError("supported interaction events are quiz, complete, and view")


def run_offline_evaluation(k=5, *, catalog=None, dataset=None):
    """Return a JSON-serializable comparison over one catalog and one case set.

    Default data is explicitly synthetic. Pass immutable catalog snapshots and
    a caller-declared dataset to evaluate supplied evidence without a database.
    Adaptive, stable-catalog, and content-based rankers receive the same eligible
    candidates for every case. Ranking metrics are macro-averages over cases with
    nonempty explicit labels, reported both per scenario and in aggregate.
    Coverage is distinct top-K resource IDs / full catalog size across all cases.
    Runtime uses perf_counter around ranking only (including adaptive EMA replay),
    excluding shared catalog loading/filtering, dataset generation, and metrics.
    Rankings and metrics are reproducible; measured runtime intentionally varies.
    """
    _validate_k(k)
    catalog = tuple(sorted(load_catalog() if catalog is None else catalog, key=lambda item: item.id))
    dataset = build_synthetic_dataset(catalog) if dataset is None else dataset
    _validate_inputs(catalog, dataset)
    algorithms = {"adaptive": adaptive_resources,
                  "stable_baseline": lambda candidates, history, limit: baseline_resources(
                      limit, candidates=candidates)}
    algorithm_names = tuple(algorithms) + ("content_based",)
    totals = {name: {"runtime_seconds": 0.0, "recommended": set(), "metrics": [],
                     "scenarios": {}}
              for name in algorithm_names}
    results = []
    for case in dataset.cases:
        history = _history_before_split(case)
        candidates = _candidates(catalog, history, case.split_at)
        candidate_ids = [resource.id for resource in candidates]
        labels = sorted(set(case.relevant_resource_ids or ())) or None
        if labels and not set(labels).issubset(candidate_ids):
            raise ValueError("relevance labels must belong to the shared eligible candidate pool")
        scenario = case.scenario or case.case_id
        result = {"case_id": case.case_id, "scenario": scenario,
                  "label_rule": case.label_rule or None,
                  "target_topic_id": case.target_topic_id,
                  "target_difficulty": case.target_difficulty,
                  "split_at": case.split_at.isoformat(),
                  "history_size": len(history), "candidate_resource_ids": candidate_ids,
                  "relevant_resource_ids": labels, "recommendations": {}, "metrics": {}}
        rankers = dict(algorithms)
        rankers["content_based"] = lambda candidate_resources, _, limit: content_based_resources(
            candidate_resources, target_topic_id=case.target_topic_id,
            target_difficulty=case.target_difficulty, k=limit)
        for name, ranker in rankers.items():
            started = perf_counter()
            recommended = [resource.id for resource in ranker(candidates, history, k)]
            elapsed = perf_counter() - started
            totals[name]["runtime_seconds"] += elapsed
            metrics = ranking_metrics(recommended, labels, k)
            totals[name]["recommended"].update(recommended)
            scenario_total = totals[name]["scenarios"].setdefault(
                scenario, {"runtime_seconds": 0.0, "recommended": set(), "metrics": [],
                            "evaluated_cases": 0, "labeled_cases": 0})
            scenario_total["runtime_seconds"] += elapsed
            scenario_total["recommended"].update(recommended)
            scenario_total["evaluated_cases"] += 1
            if labels:
                totals[name]["metrics"].append(metrics)
                scenario_total["metrics"].append(metrics)
                scenario_total["labeled_cases"] += 1
            result["recommendations"][name] = recommended
            result["metrics"][name] = metrics
        results.append(result)

    def average_metrics(metrics):
        return {
            key: sum(item[key] for item in metrics) / len(metrics) if metrics else None
            for key in ("precision_at_k", "recall_at_k", "ndcg_at_k")
        }

    def summarize_scenario(total):
        metrics = average_metrics(total["metrics"])
        metrics.update(
            coverage=len(total["recommended"]) / len(catalog) if catalog else 0.0,
            unique_recommended_resources=len(total["recommended"]),
            evaluated_cases=total["evaluated_cases"],
            labeled_cases=total["labeled_cases"],
            runtime_seconds=total["runtime_seconds"],
            mean_runtime_seconds=(total["runtime_seconds"] / total["evaluated_cases"]
                                  if total["evaluated_cases"] else 0.0),
        )
        return metrics

    per_algorithm = {}
    for name, total in totals.items():
        labeled = total["metrics"]
        per_algorithm[name] = {
            **average_metrics(labeled),
            "per_scenario": {
                scenario: summarize_scenario(scenario_total)
                for scenario, scenario_total in total["scenarios"].items()
            },
        }
        per_algorithm[name].update(
            coverage=len(total["recommended"]) / len(catalog) if catalog else 0.0,
            unique_recommended_resources=len(total["recommended"]),
            evaluated_cases=len(results), labeled_cases=len(labeled),
            runtime_seconds=total["runtime_seconds"],
            mean_runtime_seconds=total["runtime_seconds"] / len(results) if results else 0.0,
        )

    scenario_metadata = {}
    for result in results:
        scenario_metadata.setdefault(result["scenario"], {
            "case_ids": [],
            "label_rule": result["label_rule"],
            "target_topic_id": result["target_topic_id"],
            "target_difficulty": result["target_difficulty"],
            "metrics": {},
        })["case_ids"].append(result["case_id"])
    for scenario, metadata in scenario_metadata.items():
        metadata["metrics"] = {
            name: per_algorithm[name]["per_scenario"].get(scenario, {
                "precision_at_k": None, "recall_at_k": None, "ndcg_at_k": None,
            })
            for name in algorithm_names
        }

    return {
        "dataset": {"name": dataset.name, "source": dataset.source,
                     "synthetic": dataset.source == "synthetic", "size": len(dataset.cases),
                     "interaction_count": sum(len(case.interactions) for case in dataset.cases),
                     "labeled_cases": sum(bool(case.relevant_resource_ids) for case in dataset.cases),
                     "scenario_label_rules": dict(dataset.scenario_label_rules) or {
                         case.scenario: case.label_rule for case in dataset.cases if case.scenario
                     },
                     "label_provenance": "Constructed hypothetical relevance, not real observations."
                     if dataset.source == "synthetic" else "Caller-supplied held-out labels; provenance is caller-declared."},
        "dataset_size": len(dataset.cases),
        "synthetic_vs_real": "synthetic" if dataset.source == "synthetic" else "real",
        "catalog_size": len(catalog), "catalog_resource_ids": [resource.id for resource in catalog],
        "k": k,
        "scenarios": scenario_metadata,
        "assumptions": list(dataset.assumptions) + [
            "Only interactions strictly before each fixed split time influence rankings; views are not scoring signals.",
            "The offline scorer replays EMA (rate 0.35), difficulty and prerequisite penalties; "
            "no stored real-user mastery is used. Adaptive and baseline candidates suppress completions "
            "from the preceding 14 days.",
            "Binary relevance is supplied independently of rankings. None/empty labels leave ranking metrics null; "
            "labels outside the eligible catalog are rejected, never silently replaced.",
            "Ranking metrics are labeled-case macro-averages; Precision@K divides by K even for short lists.",
            "Coverage counts unique top-K recommendations across all cases divided by the full catalog size.",
            "Runtime is measured ranking-only wall-clock seconds via perf_counter; it varies across runs "
            "and excludes shared setup, candidate filtering, and metric calculation.",
        ],
        "algorithms": per_algorithm, "cases": results,
    }
