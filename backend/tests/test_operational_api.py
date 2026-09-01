from __future__ import annotations

from sqlalchemy.exc import OperationalError


def test_application_creation(app) -> None:
    assert app.title == "RazorShield"


def test_health_is_process_only(client, app, monkeypatch) -> None:
    monkeypatch.setattr(app.state.database, "ping", lambda: (_ for _ in ()).throw(OperationalError("x", {}, None)))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_with_database(client) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available", "model": "available"}


def test_ready_database_failure(client, app, monkeypatch) -> None:
    def fail() -> None:
        raise OperationalError("SELECT 1", {}, None)

    monkeypatch.setattr(app.state.database, "ping", fail)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_request_id_generation(client) -> None:
    response = client.get("/health")
    assert len(response.headers["X-Request-ID"]) == 36


def test_request_id_propagation(client) -> None:
    request_id = "buildathon-request-0001"
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] == request_id


def test_cors_uses_configured_origin_only(client) -> None:
    allowed = client.options(
        "/health",
        headers={"Origin": "http://testserver", "Access-Control-Request-Method": "GET"},
    )
    denied = client.options(
        "/health",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://testserver"
    assert "access-control-allow-origin" not in denied.headers


def test_structured_404(client) -> None:
    response = client.get("/not-a-route")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]


def test_structured_validation_error(client) -> None:
    response = client.get("/health?verbose=definitely-not-a-boolean")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
