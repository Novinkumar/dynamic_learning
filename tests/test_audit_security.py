"""Security regressions; every initialized database is disposable/in-memory."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import make_url

from app import create_app, db
from app.models import QuizAttempt, ResourceCompletion, Topic, User
from config import TestingConfig
from seed import seed


def environment_config(monkeypatch, **values):
    for name in ("APP_ENV", "SECRET_KEY", "ENABLE_DEMO_ACCOUNT", "SESSION_COOKIE_SECURE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return runpy.run_path(str(Path(__file__).parents[1] / "config.py"))


@pytest.fixture()
def app_factory():
    applications = []

    def factory(configuration):
        application = create_app(configuration)
        applications.append(application)
        return application

    yield factory
    for application in applications:
        with application.app_context():
            db.session.remove()
            for engine in db.engines.values():
                engine.dispose()


def test_production_disallows_explicit_demo_override(monkeypatch, app_factory):
    configuration = environment_config(
        monkeypatch, APP_ENV="production", ENABLE_DEMO_ACCOUNT="1",
        SECRET_KEY="fixture-production-key-7b654c03-09a1-4cef",
    )["Config"]
    assert configuration.DEMO_ACCOUNT_ENABLED is False
    assert configuration.SESSION_COOKIE_SECURE is True
    application = app_factory(configuration)
    seed(application)
    with application.app_context():
        assert User.query.filter_by(email="demo@example.com").first() is None
        assert Topic.query.count() == 7
    cookie = application.test_client().get("/api/csrf", base_url="https://localhost").headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


@pytest.mark.parametrize("secret", [
    None, "", "   ", "dev-change-this-secret", "replace-with-a-long-random-value", "test-only-secret",
])
def test_production_rejects_unsafe_secret_before_database_init(monkeypatch, secret):
    configuration = type("ProductionConfig", (TestingConfig,), {"APP_ENV": "production", "SECRET_KEY": secret})
    initialize = Mock(side_effect=AssertionError("database initialization must not run"))
    monkeypatch.setattr(db, "init_app", initialize)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app(configuration)
    initialize.assert_not_called()


def test_production_factory_enforces_policy_for_custom_configuration(app_factory):
    configuration = type("ProductionConfig", (TestingConfig,), {
        "APP_ENV": " Production ", "DEMO_ACCOUNT_ENABLED": True,
        "SECRET_KEY": "fixture-production-key-7b654c03-09a1-4cef",
    })
    application = app_factory(configuration)
    assert application.config["APP_ENV"] == "production"
    assert application.config["DEMO_ACCOUNT_ENABLED"] is False
    assert application.config["SESSION_COOKIE_SECURE"] is True


def test_testing_configuration_is_independent_of_process_environment(monkeypatch, app_factory):
    configuration = environment_config(
        monkeypatch, APP_ENV="production", SECRET_KEY="", ENABLE_DEMO_ACCOUNT="0", SESSION_COOKIE_SECURE="1",
    )["TestingConfig"]
    assert configuration.APP_ENV == "testing"
    assert configuration.SECRET_KEY
    assert configuration.DEMO_ACCOUNT_ENABLED is True
    assert configuration.SESSION_COOKIE_SECURE is False
    assert configuration.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"
    assert app_factory(configuration).test_client().get("/login").status_code == 200


def test_development_defaults_keep_local_setup(monkeypatch, app_factory):
    configuration = environment_config(monkeypatch)["Config"]
    assert configuration.APP_ENV == "development"
    assert configuration.DEMO_ACCOUNT_ENABLED is True
    assert configuration.SESSION_COOKIE_SECURE is False
    assert app_factory(configuration).test_client().get("/login").status_code == 200


@pytest.mark.parametrize("enabled", [False, True])
def test_seed_output_is_honest_and_never_prints_password(app, capsys, enabled):
    app.config["DEMO_ACCOUNT_ENABLED"] = enabled
    seed(app)
    output = capsys.readouterr().out
    assert "catalog" in output
    assert "password123" not in output
    assert ("disabled" in output) is (not enabled)
    with app.app_context():
        demo = User.query.filter_by(email="demo@example.com").first()
        assert (demo is not None) is enabled
        if demo:
            assert demo.is_admin and demo.check_password("password123")


def test_seed_does_not_enable_demo_when_production_flag_is_overridden(app):
    app.config.update(APP_ENV="production", DEMO_ACCOUNT_ENABLED=True)
    seed(app)
    with app.app_context():
        assert User.query.filter_by(email="demo@example.com").first() is None


@pytest.mark.parametrize("environment,uri", [
    ("production", "sqlite:///:memory:"),
    ("staging", "sqlite:///:memory:"),
    ("development", "postgresql://localhost/never_connected"),
    ("testing", "mysql://localhost/never_connected"),
])
def test_reset_is_rejected_before_drop(app, user, monkeypatch, environment, uri):
    # Change configuration only: the sole initialized engine remains in-memory SQLite.
    app.config.update(APP_ENV=environment, SQLALCHEMY_DATABASE_URI=uri)
    drop = Mock(side_effect=AssertionError("unsafe drop attempted"))
    monkeypatch.setattr(db, "drop_all", drop)
    with pytest.raises(ValueError, match="development/test SQLite"):
        seed(app, reset=True)
    drop.assert_not_called()
    with app.app_context():
        assert db.session.get(User, user) is not None


def test_reset_checks_all_bound_engines_before_drop(app, monkeypatch):
    # A fake engine supplies only its URL; no remote connection is created.
    with app.app_context(), monkeypatch.context() as patch:
        patch.setitem(db.engines, "remote", SimpleNamespace(url=make_url("postgresql://localhost/never_connected")))
        drop = Mock(side_effect=AssertionError("unsafe drop attempted"))
        patch.setattr(db, "drop_all", drop)
        with pytest.raises(ValueError, match="development/test SQLite"):
            seed(app, reset=True)
        drop.assert_not_called()


@pytest.mark.parametrize("environment", ["development", "test", "testing"])
def test_reset_remains_available_for_development_test_sqlite(app, user, environment):
    app.config["APP_ENV"] = environment
    seed(app, reset=True)
    with app.app_context():
        assert User.query.filter_by(email="learner@example.test").first() is None
        assert Topic.query.count() == 7
        assert User.query.filter_by(email="demo@example.com").one().is_admin


@pytest.mark.parametrize("as_json", [False, True])
def test_reserved_demo_login_is_blocked_after_disabling_seeded_account(app, client, as_json):
    seed(app)
    app.config["DEMO_ACCOUNT_ENABLED"] = False
    credentials = {"email": " DEMO@Example.com ", "password": "password123"}
    response = client.post("/login", **{"json" if as_json else "data": credentials})
    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid credentials"}
    with client.session_transaction() as session:
        assert "user_id" not in session
    assert client.get("/api/evaluation").status_code == 401
    assert client.get("/evaluation").status_code == 401


@pytest.mark.parametrize("enabled", [False, True])
def test_demo_email_cannot_be_reused_for_registration(app, client, enabled):
    app.config["DEMO_ACCOUNT_ENABLED"] = enabled
    response = client.post("/register", json={
        "email": " DEMO@Example.com ", "name": "Ordinary learner", "password": "a learner password",
    })
    assert response.status_code == 409
    with app.app_context():
        assert User.query.count() == 0


@pytest.mark.parametrize("endpoint", ["/register", "/login", "/logout"])
@pytest.mark.parametrize("payload", [[], [{"email": "learner@example.test"}], None, "text", 42, False])
def test_auth_rejects_non_object_json(client, endpoint, payload):
    response = client.post(endpoint, data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert response.is_json
    with client.session_transaction() as session:
        assert "user_id" not in session


@pytest.mark.parametrize("endpoint", ["/register", "/login"])
def test_auth_rejects_malformed_json(client, endpoint):
    response = client.post(endpoint, data="{", content_type="application/json")
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize("as_json", [False, True])
def test_registration_preserves_password_whitespace(app, client, as_json):
    credentials = {"name": " Ada ", "email": " ADA@Example.test ", "password": "  exact password\t "}
    response = client.post("/register", **{"json" if as_json else "data": credentials})
    assert response.status_code == (201 if as_json else 302)
    with app.app_context():
        account = User.query.filter_by(email="ada@example.test").one()
        assert account.name == "Ada"
        assert account.check_password(credentials["password"])
        assert not account.check_password(credentials["password"].strip())
    client.post("/logout", json={})
    response = client.post("/login", **{"json" if as_json else "data": credentials})
    assert response.status_code == (200 if as_json else 302)


@pytest.mark.parametrize("as_json", [False, True])
def test_logout_preserves_html_and_json_contracts(client, user, as_json):
    with client.session_transaction() as session:
        session["user_id"] = user
    response = client.post("/logout", **({"json": {}} if as_json else {"data": {}}))
    if as_json:
        assert response.status_code == 200
        assert response.get_json() == {"ok": True}
    else:
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
    assert client.get("/api/dashboard").status_code == 401


@pytest.mark.parametrize("endpoint", ["/evaluation", "/api/evaluation"])
def test_evaluation_requires_authenticated_admin_for_html_and_api(app, client, user, endpoint):
    assert client.get(endpoint).status_code == 401
    assert client.post("/login", json={"email": "learner@example.test", "password": "correct horse"}).status_code == 200
    assert client.get(endpoint).status_code == 403
    with app.app_context():
        db.session.get(User, user).is_admin = True
        db.session.commit()
    response = client.get(endpoint)
    assert response.status_code == 200
    if endpoint.startswith("/api/"):
        assert "offline" in response.get_json()
    else:
        assert response.mimetype == "text/html"


@pytest.mark.parametrize("endpoint", ["/register", "/login", "/logout"])
@pytest.mark.parametrize("as_json", [False, True])
def test_auth_requires_valid_csrf_for_html_and_json(app, client, user, endpoint, as_json):
    app.config["WTF_CSRF_ENABLED"] = True
    if endpoint == "/logout":
        with client.session_transaction() as session:
            session["user_id"] = user
    payload = {"name": "New learner", "email": "new@example.test", "password": "a valid password"}
    if endpoint == "/login":
        payload = {"email": "learner@example.test", "password": "correct horse"}
    token = client.get("/api/csrf").get_json()["csrf_token"]
    for invalid_token in (None, "invalid-token"):
        kwargs = {"json" if as_json else "data": dict(payload)}
        if invalid_token:
            if as_json:
                kwargs["headers"] = {"X-CSRFToken": invalid_token}
            else:
                kwargs["data"]["csrf_token"] = invalid_token
        response = client.post(endpoint, **kwargs)
        assert response.status_code == 400
        if as_json:
            assert response.is_json
        with client.session_transaction() as session:
            assert session.get("user_id") == (user if endpoint == "/logout" else None)
        with app.app_context():
            assert User.query.filter_by(email="new@example.test").first() is None
    kwargs = {"json" if as_json else "data": dict(payload)}
    if as_json:
        kwargs["headers"] = {"X-CSRFToken": token}
    else:
        kwargs["data"]["csrf_token"] = token
    response = client.post(endpoint, **kwargs)
    assert response.status_code == ((201 if endpoint == "/register" else 200) if as_json else 302)


def test_learning_writes_require_csrf_even_with_authenticated_session(app, client, user, catalog):
    app.config["WTF_CSRF_ENABLED"] = True
    with client.session_transaction() as session:
        session["user_id"] = user
    endpoints = [
        (f"/api/resources/{catalog['resource_ids'][0]}/complete", {}),
        (f"/api/quizzes/{catalog['quiz_id']}/submit", {"answers": {
            str(question_id): answer for question_id, answer in zip(catalog["question_ids"], catalog["answers"])
        }}),
    ]
    for endpoint, payload in endpoints:
        response = client.post(endpoint, json=payload)
        assert response.status_code == 400 and response.is_json
    with app.app_context():
        assert ResourceCompletion.query.count() == 0
        assert QuizAttempt.query.count() == 0
    token = client.get("/api/csrf").get_json()["csrf_token"]
    for endpoint, payload in endpoints:
        assert client.post(endpoint, json=payload, headers={"X-CSRFToken": token}).status_code == 200
    with app.app_context():
        assert ResourceCompletion.query.count() == 1
        assert QuizAttempt.query.count() == 1
