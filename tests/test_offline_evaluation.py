"""Offline comparisons must use declared evidence and a shared candidate pool."""

from dataclasses import replace
from datetime import timedelta
import math

import pytest

from app.models import MasteryScore, QuizAttempt, Resource, ResourceCompletion, ResourceInteraction, User
from app.services import offline_evaluation as evaluation
from app.services.baseline import baseline_resources
from seed import seed


def example_catalog():
    return (
        evaluation.CatalogResource(1, 1, 1, "Foundations"),
        evaluation.CatalogResource(2, 1, 2, "Foundations"),
        evaluation.CatalogResource(3, 2, 1, "Practice", ((1, 0.6),)),
        evaluation.CatalogResource(4, 2, 2, "Practice", ((1, 0.6),)),
    )


def declared_dataset(*cases, source="real"):
    return evaluation.EvaluationDataset("explicit-test-labels", source, tuple(cases))


def test_binary_metrics_match_hand_calculated_values():
    metrics = evaluation.ranking_metrics([1, 2, 3, 4], [2, 4, 5], k=4)
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    ideal = 1 + 1 / math.log2(3) + 1 / math.log2(4)
    assert metrics["precision_at_k"] == pytest.approx(0.5)
    assert metrics["recall_at_k"] == pytest.approx(2 / 3)
    assert metrics["ndcg_at_k"] == pytest.approx(dcg / ideal)
    assert evaluation.ranking_metrics([2, 4, 5], [2, 4, 5], 3)["ndcg_at_k"] == 1.0
    assert evaluation.ranking_metrics([1], [2], 1) == {
        "precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0,
    }


def test_precision_uses_requested_cutoff_for_short_or_empty_lists():
    assert evaluation.ranking_metrics([2], [2, 3], 5) == {
        "precision_at_k": 0.2, "recall_at_k": 0.5,
        "ndcg_at_k": pytest.approx(1 / (1 + 1 / math.log2(3))),
    }
    assert evaluation.ranking_metrics([], [2], 5) == {
        "precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0,
    }


@pytest.mark.parametrize("labels", [None, ()])
def test_missing_labels_are_not_inferred_from_interactions(labels):
    split = evaluation.SYNTHETIC_SPLIT_AT
    case = evaluation.EvaluationCase("unlabeled-real-history", split, (
        evaluation.Interaction("quiz", split - timedelta(days=1), topic_id=1, score=0.1),
        evaluation.Interaction("view", split - timedelta(hours=2), resource_id=2),
        evaluation.Interaction("complete", split - timedelta(days=21), resource_id=1),
        evaluation.Interaction("complete", split + timedelta(days=1), resource_id=2),
    ), labels)
    report = evaluation.run_offline_evaluation(2, catalog=example_catalog(), dataset=declared_dataset(case))
    assert report["dataset"]["source"] == "real"
    assert report["dataset"]["synthetic"] is False
    assert report["dataset"]["labeled_cases"] == 0
    assert report["cases"][0]["relevant_resource_ids"] is None
    for metrics in report["algorithms"].values():
        assert metrics["precision_at_k"] is None
        assert metrics["recall_at_k"] is None
        assert metrics["ndcg_at_k"] is None
        assert metrics["coverage"] > 0
        assert metrics["runtime_seconds"] >= 0


def test_rankers_receive_identical_candidates_and_case_histories(monkeypatch):
    split = evaluation.SYNTHETIC_SPLIT_AT
    case = evaluation.EvaluationCase("shared-pool", split, (
        evaluation.Interaction("complete", split - timedelta(days=14), resource_id=1),
        evaluation.Interaction("complete", split - timedelta(days=15), resource_id=2),
    ), (2,))
    seen = {}
    adaptive = evaluation.adaptive_resources
    baseline = evaluation.baseline_resources

    def record_adaptive(candidates, history, k):
        seen["adaptive"] = candidates
        seen["history"] = history
        return adaptive(candidates, history, k)

    def record_baseline(limit, *, candidates):
        seen["baseline"] = candidates
        return baseline(limit, candidates=candidates)

    monkeypatch.setattr(evaluation, "adaptive_resources", record_adaptive)
    monkeypatch.setattr(evaluation, "baseline_resources", record_baseline)
    report = evaluation.run_offline_evaluation(4, catalog=example_catalog(), dataset=declared_dataset(case))
    assert seen["adaptive"] is seen["baseline"]
    assert [resource.id for resource in seen["adaptive"]] == [2, 3, 4]
    assert len(seen["history"]) == 2
    result = report["cases"][0]
    assert result["candidate_resource_ids"] == [2, 3, 4]
    for recommendations in result["recommendations"].values():
        assert set(recommendations) == {2, 3, 4}
    assert result["recommendations"]["stable_baseline"] == [2, 3, 4]


def test_content_baseline_prioritizes_explicit_topic_and_suitable_difficulty():
    ranked = evaluation.content_based_resources(
        example_catalog(), target_topic_id=2, target_difficulty=2, k=4,
    )
    assert [resource.id for resource in ranked] == [4, 3, 2, 1]


def test_future_activity_cannot_leak_into_ranking_or_labels():
    split = evaluation.SYNTHETIC_SPLIT_AT
    before = tuple(evaluation.Interaction("quiz", split - timedelta(days=5 - i),
                                         topic_id=1, score=1.0) for i in range(4))
    case = evaluation.EvaluationCase("chronological", split, before, (3,))
    future = before + (
        evaluation.Interaction("quiz", split, topic_id=2, score=1.0),
        evaluation.Interaction("complete", split + timedelta(days=1), resource_id=3),
    )
    report = evaluation.run_offline_evaluation(1, catalog=example_catalog(), dataset=declared_dataset(case))
    later = evaluation.run_offline_evaluation(
        1, catalog=example_catalog(), dataset=declared_dataset(replace(case, interactions=future)))
    assert report["cases"] == later["cases"]
    assert report["cases"][0]["recommendations"]["adaptive"] == [3]
    assert report["cases"][0]["recommendations"]["stable_baseline"] == [1]


def test_aggregate_metrics_exclude_unlabeled_cases_and_coverage_includes_them():
    split = evaluation.SYNTHETIC_SPLIT_AT
    cases = (
        evaluation.EvaluationCase("hit", split, relevant_resource_ids=(1,)),
        evaluation.EvaluationCase("miss", split, relevant_resource_ids=(2,)),
        evaluation.EvaluationCase("unlabeled", split, (
            evaluation.Interaction("complete", split - timedelta(days=1), resource_id=1),
        )),
    )
    report = evaluation.run_offline_evaluation(1, catalog=example_catalog(), dataset=declared_dataset(*cases))
    baseline = report["algorithms"]["stable_baseline"]
    assert baseline["precision_at_k"] == 0.5
    assert baseline["recall_at_k"] == 0.5
    assert baseline["ndcg_at_k"] == 0.5
    assert baseline["labeled_cases"] == 2
    assert baseline["evaluated_cases"] == 3
    assert baseline["unique_recommended_resources"] == 2
    assert baseline["coverage"] == 0.5


def test_default_synthetic_dataset_is_reproducible_read_only_and_independently_labeled(app):
    seed(app)
    with app.app_context():
        models = (Resource, User, QuizAttempt, ResourceCompletion, MasteryScore, ResourceInteraction)
        counts_before = [model.query.count() for model in models]
        catalog = evaluation.load_catalog()
        dataset = evaluation.build_synthetic_dataset(catalog)
        assert dataset == evaluation.build_synthetic_dataset(tuple(reversed(catalog)))
        assert len(dataset.cases) == 4
        assert [case.scenario for case in dataset.cases] == [
            "beginner_cold_start", "struggling_with_topic",
            "ready_for_advanced_material", "revision_due",
        ]
        assert len({case.relevant_resource_ids for case in dataset.cases}) > 1
        assert all(case.label_rule for case in dataset.cases)
        assert {name for name, _ in dataset.scenario_label_rules} == {
            "beginner_cold_start", "struggling_with_topic",
            "ready_for_advanced_material", "revision_due",
        }
        for case in dataset.cases[1:]:
            assert case.interactions
            assert all(item.occurred_at < case.split_at for item in case.interactions)
        first = evaluation.run_offline_evaluation()
        second = evaluation.run_offline_evaluation()
        assert first["dataset"] == second["dataset"]
        assert first["cases"] == second["cases"]
        assert first["dataset"]["source"] == "synthetic"
        assert first["dataset"]["synthetic"] is True
        assert first["dataset"]["size"] == 4
        assert first["dataset"]["labeled_cases"] == 4
        assert first["catalog_size"] == 21
        assert first["k"] == 5
        assert set(first["scenarios"]) == {name for name, _ in dataset.scenario_label_rules}
        assert set(first["algorithms"]) == {"adaptive", "stable_baseline", "content_based"}
        for scenario in first["scenarios"].values():
            assert set(scenario["metrics"]) == set(first["algorithms"])
        assert first["assumptions"]
        for name, metrics in first["algorithms"].items():
            assert metrics["runtime_seconds"] > 0
            assert set(metrics["per_scenario"]) == set(first["scenarios"])
            for key in ("precision_at_k", "recall_at_k", "ndcg_at_k", "coverage"):
                assert 0 <= metrics[key] <= 1
                assert metrics[key] == second["algorithms"][name][key]
        assert [model.query.count() for model in models] == counts_before
        assert all(not hasattr(resource, "priority") for resource in Resource.query.all())


def test_runtime_is_measured_in_seconds_with_an_actual_timer(monkeypatch):
    ticks = iter([10.0, 10.25, 11.0, 11.5, 12.0, 12.75])
    monkeypatch.setattr(evaluation, "perf_counter", lambda: next(ticks))
    case = evaluation.EvaluationCase("timing", evaluation.SYNTHETIC_SPLIT_AT, relevant_resource_ids=(1,))
    report = evaluation.run_offline_evaluation(1, catalog=example_catalog(), dataset=declared_dataset(case))
    assert report["algorithms"]["adaptive"]["runtime_seconds"] == 0.25
    assert report["algorithms"]["stable_baseline"]["runtime_seconds"] == 0.5
    assert report["algorithms"]["adaptive"]["mean_runtime_seconds"] == 0.25
    assert report["algorithms"]["content_based"]["runtime_seconds"] == 0.75


@pytest.mark.parametrize("k", [0, -1, 1.5, "5", None, True])
def test_invalid_cutoffs_are_rejected(k):
    with pytest.raises(ValueError, match="positive integer"):
        evaluation.run_offline_evaluation(k, catalog=example_catalog())


@pytest.mark.parametrize("labels", [(999,), (1,)])
def test_invalid_or_ineligible_labels_are_rejected_not_replaced(labels):
    split = evaluation.SYNTHETIC_SPLIT_AT
    case = evaluation.EvaluationCase("invalid-label", split, (
        evaluation.Interaction("complete", split - timedelta(days=1), resource_id=1),
    ), labels)
    with pytest.raises(ValueError, match="relevance labels"):
        evaluation.run_offline_evaluation(catalog=example_catalog(), dataset=declared_dataset(case))


def test_empty_catalog_has_no_fabricated_cases_labels_or_metrics():
    report = evaluation.run_offline_evaluation(catalog=())
    assert report["dataset"]["size"] == 0
    assert report["catalog_size"] == 0
    assert report["cases"] == []
    for metrics in report["algorithms"].values():
        assert metrics["precision_at_k"] is None
        assert metrics["recall_at_k"] is None
        assert metrics["ndcg_at_k"] is None
        assert metrics["coverage"] == 0.0
        assert metrics["runtime_seconds"] == 0.0


def test_stable_baseline_preserves_database_default_and_honors_explicit_pool(app, catalog):
    with app.app_context():
        assert [resource.id for resource in baseline_resources()] == catalog["resource_ids"]
        assert [resource.id for resource in baseline_resources(0)] == catalog["resource_ids"][:1]
    snapshots = tuple(evaluation.CatalogResource(i, 1, 1) for i in range(60, 0, -1))
    assert [resource.id for resource in baseline_resources(60, candidates=snapshots)] == list(range(1, 61))
    assert baseline_resources(candidates=()) == []
