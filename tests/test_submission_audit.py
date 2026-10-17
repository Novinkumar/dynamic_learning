"""Submission checks using disposable databases; never reset the workspace DB."""
from dataclasses import replace
from datetime import timedelta
from math import log2

import pytest

from app import db
from app.models import MasteryScore, Quiz, QuizAttempt, ResourceCompletion, Topic, User
from app.services import offline_evaluation as offline
from app.services import recommender
from app.services.mastery import get_mastery, update_mastery
from seed import seed


def independent_metrics(ids, labels, k):
    labels = set(labels or [])
    if not labels:
        return dict.fromkeys(("precision_at_k", "recall_at_k", "ndcg_at_k"))
    gains = [int(resource_id in labels) for resource_id in ids[:k]]
    dcg = sum(gain / log2(rank + 2) for rank, gain in enumerate(gains))
    idcg = sum(1 / log2(rank + 2) for rank in range(min(k, len(labels))))
    return {"precision_at_k": sum(gains) / k, "recall_at_k": sum(gains) / len(labels),
            "ndcg_at_k": dcg / idcg}


def test_benchmark_arithmetic_and_report(app):
    seed(app)
    report = offline.run_offline_evaluation()
    assert report["dataset_size"] == 4 and report["catalog_size"] == 21
    for name, aggregate in report["algorithms"].items():
        expected = []
        unique = set()
        for case in report["cases"]:
            ids = case["recommendations"][name]
            unique.update(ids)
            value = independent_metrics(ids, case["relevant_resource_ids"], report["k"])
            assert case["metrics"][name] == pytest.approx(value)
            if case["relevant_resource_ids"]:
                expected.append(value)
        for key in ("precision_at_k", "recall_at_k", "ndcg_at_k"):
            assert aggregate[key] == pytest.approx(sum(item[key] for item in expected) / len(expected))
        assert aggregate["coverage"] == len(unique) / report["catalog_size"]
        assert aggregate["unique_recommended_resources"] == len(unique)
        assert aggregate["runtime_seconds"] > 0
        assert aggregate["mean_runtime_seconds"] == aggregate["runtime_seconds"] / report["dataset_size"]
        for scenario, values in aggregate["per_scenario"].items():
            cases = [case for case in report["cases"] if case["scenario"] == scenario]
            assert values["evaluated_cases"] == len(cases)
            for key in ("precision_at_k", "recall_at_k", "ndcg_at_k"):
                assert values[key] == pytest.approx(sum(case["metrics"][name][key] for case in cases) / len(cases))
            covered = {rid for case in cases for rid in case["recommendations"][name]}
            assert values["coverage"] == len(covered) / report["catalog_size"]
        print(name, {key: round(aggregate[key], 6) for key in
                     ("precision_at_k", "recall_at_k", "ndcg_at_k", "coverage", "mean_runtime_seconds")})
    for name, values in report["scenarios"].items():
        print(name, {method: [round(metrics[key], 6) for key in
                             ("precision_at_k", "recall_at_k", "ndcg_at_k")]
                     for method, metrics in values["metrics"].items()})


def test_all_three_rankers_share_pool_cutoff_and_exclude_future_activity(app, monkeypatch):
    seed(app)
    catalog = offline.load_catalog()
    split = offline.SYNTHETIC_SPLIT_AT
    first = offline.build_synthetic_dataset(catalog).cases[0]
    case = replace(first, interactions=(
        offline.Interaction("complete", split - timedelta(days=1), resource_id=catalog[-1].id),
        offline.Interaction("quiz", split - timedelta(days=1), topic_id=catalog[0].topic_id, score=.5),
        offline.Interaction("complete", split, resource_id=catalog[0].id),
        offline.Interaction("quiz", split + timedelta(days=1), topic_id=catalog[0].topic_id, score=1),
    ))
    observed = {}
    adaptive, stable, content = offline.adaptive_resources, offline.baseline_resources, offline.content_based_resources

    def adaptive_spy(candidates, history, k):
        observed["adaptive"] = (candidates, k)
        assert all(event.occurred_at < split for event in history)
        return adaptive(candidates, history, k)

    def stable_spy(limit, *, candidates):
        observed["stable"] = (candidates, limit)
        return stable(limit, candidates=candidates)

    def content_spy(candidates, **kwargs):
        observed["content"] = (candidates, kwargs["k"])
        return content(candidates, **kwargs)

    monkeypatch.setattr(offline, "adaptive_resources", adaptive_spy)
    monkeypatch.setattr(offline, "baseline_resources", stable_spy)
    monkeypatch.setattr(offline, "content_based_resources", content_spy)
    dataset = offline.EvaluationDataset("audit", "synthetic", (case,))
    report = offline.run_offline_evaluation(3, catalog=catalog, dataset=dataset)
    pool = observed["adaptive"][0]
    assert pool is observed["stable"][0] is observed["content"][0]
    assert all(k == 3 for _, k in observed.values())
    assert catalog[-1].id not in [resource.id for resource in pool]
    assert catalog[0].id in [resource.id for resource in pool]
    clean_case = replace(case, interactions=case.interactions[:2])
    clean_report = offline.run_offline_evaluation(3, catalog=catalog,
                                                dataset=replace(dataset, cases=(clean_case,)))
    assert report["cases"] == clean_report["cases"]


def test_labels_do_not_depend_on_ranking_outputs(app, monkeypatch):
    seed(app)
    catalog = offline.load_catalog()
    before = offline.build_synthetic_dataset(catalog)
    expected = offline.run_offline_evaluation(catalog=catalog, dataset=before)
    monkeypatch.setattr(offline, "adaptive_resources", lambda candidates, history, k: list(reversed(candidates))[:k])
    monkeypatch.setattr(offline, "baseline_resources", lambda k, *, candidates: list(reversed(candidates))[:k])
    monkeypatch.setattr(offline, "content_based_resources", lambda candidates, **kw: list(reversed(candidates))[:kw["k"]])
    after = offline.build_synthetic_dataset(catalog)
    modified = offline.run_offline_evaluation(catalog=catalog, dataset=after)
    assert before == after
    assert [case["relevant_resource_ids"] for case in expected["cases"]] == [case["relevant_resource_ids"] for case in modified["cases"]]
    assert expected["cases"][0]["recommendations"] != modified["cases"][0]["recommendations"]


def test_offline_adaptive_matches_live_ranker_not_an_unrelated_proxy(app, monkeypatch):
    seed(app)
    catalog = offline.load_catalog()
    dataset = offline.build_synthetic_dataset(catalog)
    report = offline.run_offline_evaluation(catalog=catalog, dataset=dataset)
    monkeypatch.setattr(recommender, "utcnow_naive", lambda: offline.SYNTHETIC_SPLIT_AT)
    for case, result in zip(dataset.cases, report["cases"]):
        user = User(email=f"{case.case_id}@example.test", name="Synthetic audit only", password_hash="not-a-login")
        db.session.add(user)
        db.session.flush()
        for event in case.interactions:
            if event.event == "quiz":
                quiz = Quiz.query.filter_by(topic_id=event.topic_id).first()
                db.session.add(QuizAttempt(user_id=user.id, quiz_id=quiz.id, score=event.score,
                                          answers={}, completed_at=event.occurred_at))
            elif event.event == "complete":
                db.session.add(ResourceCompletion(user_id=user.id, resource_id=event.resource_id,
                                                  completed_at=event.occurred_at))
        db.session.commit()
        assert [item.id for item in recommender.recommend_resources(user.id, report["k"])] == result["recommendations"]["adaptive"]


@pytest.mark.parametrize("rate,expected", [(0.2, 0.3904), (0.35, 0.5803), (0.5, 0.7), (0.8, 0.7936)])
def test_three_observation_sensitivity_matches_formula_and_implementation(app, user, rate, expected):
    seed(app)
    topic = Topic.query.filter_by(name="Variables").one()
    exact = .8 * (1 - (1 - rate) ** 3)
    assert round(exact, 4) == expected
    for _ in range(3):
        update_mastery(user, topic.id, .8, learning_rate=rate)
    assert get_mastery(user, topic.id) == expected
    ranks = recommender.recommendation_plan(user)
    resources = recommender.recommend_resources(user, 50)
    print("manual-sensitivity", rate, expected, [item.id for item in ranks["all"]],
          [(item.id, item.priority) for item in resources if item.topic_id == topic.id])


def test_attempt_replay_uses_fixed_default_rate_not_manual_sensitivity_rate(app, user):
    seed(app)
    quiz = Quiz.query.join(Topic).filter(Topic.name == "Variables").one()
    for index in range(3):
        db.session.add(QuizAttempt(user_id=user, quiz_id=quiz.id, score=.8, answers={},
                                  completed_at=offline.SYNTHETIC_SPLIT_AT + timedelta(minutes=index)))
    db.session.commit()
    # The live quiz algorithm is fixed at .35; passing .8 is not a global setting.
    update_mastery(user, quiz.topic_id, .8, learning_rate=.8)
    assert get_mastery(user, quiz.topic_id) == .5803


def test_disabling_demo_revokes_existing_demo_session(client, app):
    seed(app)
    assert client.post("/login", json={"email": "demo@example.com", "password": "password123"}).status_code == 200
    app.config["DEMO_ACCOUNT_ENABLED"] = False
    assert client.get("/api/evaluation").status_code == 401
    assert client.get("/evaluation").status_code == 401
    assert client.get("/api/progress").status_code == 401


def test_clean_cli_database_and_real_http_demo(tmp_path):
    """README seed/server/reset commands on an isolated disk DB, with CSRF ON."""
    import http.cookiejar
    from contextlib import contextmanager
    import json
    import os
    from pathlib import Path
    import socket
    import subprocess
    import sys
    import time
    import urllib.error
    import urllib.request

    from app import create_app
    from config import TestingConfig
    from app.models import Question, QuestionResponse, Resource, ResourceInteraction

    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "submission-demo.sqlite3"
    uri = "sqlite:///" + database.as_posix()
    env = {**os.environ, "DATABASE_URL": uri, "APP_ENV": "development", "ENABLE_DEMO_ACCOUNT": "1",
           "SECRET_KEY": "isolated-http-audit-secret-not-for-production", "FLASK_DEBUG": "0",
           "SESSION_COOKIE_SECURE": "0", "FLASK_SKIP_DOTENV": "1"}

    def seed_cli(*args):
        result = subprocess.run([sys.executable, "seed.py", *args], cwd=root, env=env,
                                text=True, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert "password123" not in result.stdout
        return result

    seed_cli()
    seed_cli()
    class DiskConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = uri

    @contextmanager
    def disk_context():
        with create_app(DiskConfig).app_context():
            try:
                yield
            finally:
                db.session.remove()
                db.engine.dispose()

    with disk_context():
        assert Topic.query.count() == 7 and Resource.query.count() == 21
        assert Quiz.query.count() == 7 and Question.query.count() == 25
        quiz = Quiz.query.join(Topic).filter(Topic.name == "Variables").one()
        quiz_id = quiz.id
        correct = {str(q.id): q.answer for q in quiz.questions}
        partial = {str(q.id): (q.answer if index == 0 else next(x for x in q.options if x != q.answer))
                   for index, q in enumerate(quiz.questions)}
        resource_id = Resource.query.filter_by(topic_id=quiz.topic_id, difficulty=1).one().id

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen([sys.executable, "-m", "flask", "--app", "run.py", "run", "--host", "127.0.0.1",
                                "--port", str(port), "--no-debugger", "--no-reload"],
                               cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(path, payload=None, *, token=None, browser=opener):
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        if token:
            headers["X-CSRFToken"] = token
        try:
            response = browser.open(urllib.request.Request(base + path, data=data, headers=headers), timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.status, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body

    def token(browser=opener):
        status, data = request("/api/csrf", browser=browser)
        assert status == 200
        return data["csrf_token"]

    try:
        for _ in range(60):
            try:
                if request("/login")[0] == 200:
                    break
            except urllib.error.URLError:
                pass
            time.sleep(.1)
        else:
            pytest.fail("Isolated Flask server did not start")
        assert request("/api/evaluation")[0] == 401
        assert request("/evaluation")[0] == 401
        credentials = {"email": "demo@example.com", "password": "password123"}
        assert request("/login", credentials)[0] == 400
        assert request("/login", credentials, token=token())[0] == 200
        session_token = token()
        cold = request("/api/progress")[1]
        assert cold["weak_topics"] == [] and cold["progress"]["resources_completed"] == 0
        assert request(f"/api/quizzes/{quiz_id}/submit", {"answers": correct})[0] == 400
        first_status, first = request(f"/api/quizzes/{quiz_id}/submit", {"answers": partial}, token=session_token)
        assert first_status == 200 and first["score"] == .25
        assert first["mastery"] == .0875 and first["adaptation"]["previous_score"] is None
        second_status, second = request(f"/api/quizzes/{quiz_id}/submit", {"answers": correct}, token=session_token)
        assert second_status == 200 and second["score"] == 1
        assert second["adaptation"]["previous_score"] == .25
        assert second["adaptation"]["latest_mastery"] == .4069
        assert second["adaptation"]["recommendations_changed"]
        for _ in range(2):
            assert request(f"/api/resources/{resource_id}/complete", {}, token=session_token)[0] == 200
        refreshed = request("/api/progress")[1]
        assert refreshed["progress"]["resources_completed"] == 1
        assert refreshed["overall_progress"] == round(1 / 21, 4)
        assert refreshed["completed_resource_ids"] == [resource_id]
        assert len(refreshed["quiz_history"]) == 2
        library = request("/library")[1]
        assert 'disabled>Completed' in library
        assert "1 of 21 catalog resources completed" in request("/dashboard")[1]
        for path in ("/evaluation", "/api/evaluation"):
            status, body = request(path)
            assert status == 200
            if path == "/evaluation":
                assert isinstance(body, str) and "Results by learner situation" in body
            else:
                assert body["offline"]["dataset_size"] == 4
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        assert request("/register", {"name": "Isolated learner", "email": "audit@example.test",
                                     "password": "audit-only-pass"}, token=token(other), browser=other)[0] == 201
        assert request("/api/evaluation", browser=other)[0] == 403
        assert request("/evaluation", browser=other)[0] == 403
        assert request("/api/progress?user_id=1", browser=other)[1]["progress"]["quizzes_completed"] == 0
        assert request("/logout", {}, token=token())[0] == 200
        assert request("/api/progress")[0] == 401
    finally:
        process.terminate()
        process.wait(timeout=15)

    # New app/session reads the disk DB after the HTTP server has stopped.
    seed_cli()
    with disk_context():
        assert QuizAttempt.query.count() == 2
        assert QuestionResponse.query.count() == 8
        assert ResourceCompletion.query.count() == 1
        assert MasteryScore.query.one().score == .4069
        assert User.query.count() == 2
    seed_cli("--reset")
    with disk_context():
        assert QuizAttempt.query.count() == QuestionResponse.query.count() == 0
        assert ResourceCompletion.query.count() == MasteryScore.query.count() == ResourceInteraction.query.count() == 0
        assert User.query.count() == 1 and Topic.query.count() == 7 and Resource.query.count() == 21
    print("CLI + real HTTP + CSRF + disk persistence + idempotent seed + isolated reset: passed")
