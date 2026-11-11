import pytest

from app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "test-version")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Hello from Kaizen!"
    assert body["version"] == "test-version"
    assert body["hostname"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize("a,b,total", [(2, 3, 5), (-4, 2, -2), (0, 0, 0)])
def test_add(client, a, b, total):
    response = client.post("/api/add", json={"a": a, "b": b})
    assert response.status_code == 200
    assert response.get_json() == {"result": total}


@pytest.mark.parametrize(
    "body",
    [{}, {"a": 1}, {"a": "2", "b": 3}, {"a": True, "b": 2}, [1, 2]],
)
def test_reject_invalid_input(client, body):
    response = client.post("/api/add", json=body)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_reject_non_json(client):
    assert client.post("/api/add", data="hello").status_code == 400


def test_missing_route(client):
    assert client.get("/missing").status_code == 404
