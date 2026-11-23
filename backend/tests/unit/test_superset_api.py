"""Tests des routes /v1/superset : accès par rôle, clés du catalogue, erreurs, aucun secret exposé."""
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import get_settings
from app.core.errors import ConfigurationError, SupersetAuthError, SupersetRejected, SupersetUnavailable
from app.main import create_app
from app.services import auth_service, superset_service

SECRET = "s" * 48
UUID_A = "b973604e-c78d-47ce-8fdf-876722c1aaed"


class StubClient:
    def __init__(self, token="GUEST", error=None):
        self.token, self.error, self.calls = token, error, []

    def guest_token(self, uuid, **kw):
        self.calls.append((uuid, kw))
        if self.error:
            raise self.error
        return self.token


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("SUPERSET_URL", "http://backend-side:8088")
    monkeypatch.setenv("SUPERSET_PUBLIC_URL", "http://browser-side:18088")
    get_settings.cache_clear()
    auth_service.throttle.clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def api(env):
    return TestClient(create_app())


def bearer(role, email="u@mhm.org"):
    token, _ = security.create_access_token(subject=email, role=role, name="Nom")
    return {"Authorization": f"Bearer {token}"}


def use_client(monkeypatch, stub):
    monkeypatch.setattr(superset_service, "get_client", lambda: stub)


# ----- Accès ---------------------------------------------------------------------------------
@pytest.mark.parametrize("method,path,body", [
    ("get", "/v1/superset/dashboards", None),
    ("post", "/v1/superset/guest-token", {"dashboard": "visite"}),
])
def test_anonymous_gets_401(api, method, path, body):
    assert getattr(api, method)(path, **({"json": body} if body else {})).status_code == 401


@pytest.mark.parametrize("method,path,body", [
    ("get", "/v1/superset/dashboards", None),
    ("post", "/v1/superset/guest-token", {"dashboard": "visite"}),
])
def test_doctor_gets_403_and_superset_is_never_called(api, monkeypatch, method, path, body):
    stub = StubClient()
    use_client(monkeypatch, stub)
    r = getattr(api, method)(path, headers=bearer("doctor"), **({"json": body} if body else {}))
    assert r.status_code == 403
    assert stub.calls == []


# ----- Catalogue -----------------------------------------------------------------------------
def test_admin_lists_catalog_without_uuid(api):
    r = api.get("/v1/superset/dashboards", headers=bearer("admin"))
    assert r.status_code == 200
    data = r.json()
    assert {d["key"] for d in data} >= {"visite", "medicale"}
    assert UUID_A not in r.text  # l'UUID n'est donné qu'avec un jeton


# ----- Jeton invité --------------------------------------------------------------------------
def test_admin_gets_guest_token_for_catalog_key(api, monkeypatch):
    stub = StubClient("TOKEN-123")
    use_client(monkeypatch, stub)
    r = api.post("/v1/superset/guest-token", json={"dashboard": "visite"}, headers=bearer("admin", "a@mhm.org"))
    assert r.status_code == 200
    body = r.json()
    assert body["token"] == "TOKEN-123"
    assert body["dashboard_id"] == UUID_A
    assert body["superset_domain"] == "http://browser-side:18088"  # adresse vue par le navigateur
    assert r.headers["cache-control"] == "no-store"
    assert stub.calls[0][0] == UUID_A
    assert stub.calls[0][1]["username"] == "a@mhm.org"


@pytest.mark.parametrize("value", ["inconnu", UUID_A, "http://evil.example/x", "../../etc/passwd", "VISITE"])
def test_only_catalog_keys_are_accepted(api, monkeypatch, value):
    stub = StubClient()
    use_client(monkeypatch, stub)
    r = api.post("/v1/superset/guest-token", json={"dashboard": value}, headers=bearer("admin"))
    assert r.status_code == 404
    assert stub.calls == []  # Superset n'est même pas contacté


def test_missing_or_empty_body_is_rejected(api):
    h = bearer("admin")
    assert api.post("/v1/superset/guest-token", json={}, headers=h).status_code == 422
    assert api.post("/v1/superset/guest-token", json={"dashboard": ""}, headers=h).status_code == 422


@pytest.mark.parametrize("error,code", [
    (SupersetUnavailable("down"), 503),
    (SupersetAuthError("bad creds secret-pw"), 502),
    (SupersetRejected("embedding off"), 502),
    (ConfigurationError("SUPERSET_PASSWORD manquant"), 502),
])
def test_superset_errors_become_clean_http_errors(api, monkeypatch, error, code):
    use_client(monkeypatch, StubClient(error=error))
    r = api.post("/v1/superset/guest-token", json={"dashboard": "visite"}, headers=bearer("admin"))
    assert r.status_code == code
    assert "secret-pw" not in r.text and "SUPERSET_PASSWORD" not in r.text  # détail uniquement dans les journaux


def test_audit_trail_records_who_opened_what(api, monkeypatch, env):
    use_client(monkeypatch, StubClient())
    api.post("/v1/superset/guest-token", json={"dashboard": "visite"}, headers=bearer("admin", "a@mhm.org"))
    api.post("/v1/superset/guest-token", json={"dashboard": "nope"}, headers=bearer("admin", "a@mhm.org"))
    lines = (env / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert '"guest_token_ok"' in lines[0] and '"a@mhm.org"' in lines[0]
    assert '"unknown_dashboard"' in lines[1]
