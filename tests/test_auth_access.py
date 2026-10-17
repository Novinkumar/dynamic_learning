from .conftest import login


def test_register_login_and_protected_redirect(client, app):
    response = client.post("/register", data={"name": "Ada", "email": "ada@example.test", "password": "long enough"})
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 200

    client.post("/logout")
    protected = client.get("/api/resources")
    assert protected.status_code == 401
    assert protected.get_json()["error"] == "authentication_required"


def test_bad_login_does_not_create_session(client, user):
    response = client.post("/login", json={"email": "learner@example.test", "password": "wrong password"})
    assert response.status_code == 401
    assert client.get("/api/resources").status_code == 401


def test_admin_only_evaluation_endpoint(client, user):
    login(client)
    assert client.get("/api/evaluation").status_code == 403
