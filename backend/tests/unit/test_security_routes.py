"""Étape 7 : sécurité des routes protégées (Superset, KPIs, actualités).

Pour chaque route : sans jeton, jeton falsifié, expiré, signé avec un autre secret, algorithme « none »,
jeton sans rôle, mauvais rôle. Puis : aucun secret dans les réponses, les journaux ni l'audit.
"""
import datetime as dt
import logging

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import get_settings
from app.core.errors import SupersetAuthError
from app.main import create_app
from app.services import auth_service, superset_service

SECRET = "s" * 48
BACKEND_PASSWORD = "pw-superset-tres-secret"

# (méthode, chemin, corps, rôle autorisé)
ROUTES = [
    ("get", "/v1/superset/dashboards", None, "admin"),
    ("post", "/v1/superset/guest-token", {"dashboard": "visite"}, "admin"),
    ("get", "/v1/kpis", None, "admin"),
    ("get", "/v1/news", None, "doctor"),
]
IDS = [f"{m.upper()} {p}" for m, p, _, _ in ROUTES]


class Stub:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def guest_token(self, uuid, **kw):
        self.calls += 1
        if self.error:
            raise self.error
        return "GUEST-TOKEN"


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("SUPERSET_PASSWORD", BACKEND_PASSWORD)
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    auth_service.throttle.clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def api(env):
    return TestClient(create_app())


def call(api, method, path, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return getattr(api, method)(path, headers=headers, **({"json": body} if body else {}))


def token_for(role, **claims):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": "u@mhm.org", "role": role, "name": "N", "iat": now,
               "exp": now + dt.timedelta(minutes=5), **claims}
    return payload


def encode(payload, secret=SECRET, algorithm="HS256"):
    return jwt.encode(payload, secret, algorithm=algorithm)


# ----- Jetons refusés (401) sur toutes les routes protégées ------------------------------------
@pytest.mark.parametrize("method,path,body,role", ROUTES, ids=IDS)
class TestInvalidTokens:
    def test_no_token(self, api, method, path, body, role):
        assert call(api, method, path, body).status_code == 401

    def test_garbage_token(self, api, method, path, body, role):
        assert call(api, method, path, body, "abc.def.ghi").status_code == 401

    def test_tampered_signature(self, api, method, path, body, role):
        good = encode(token_for(role))
        assert call(api, method, path, body, good[:-3] + "xyz").status_code == 401

    def test_expired_token(self, api, method, path, body, role):
        past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        assert call(api, method, path, body, encode(token_for(role, exp=past))).status_code == 401

    def test_token_signed_with_another_secret(self, api, method, path, body, role):
        assert call(api, method, path, body, encode(token_for(role), secret="x" * 48)).status_code == 401

    def test_algorithm_none_is_refused(self, api, method, path, body, role):
        forged = jwt.encode(token_for(role), key=None, algorithm="none")
        assert call(api, method, path, body, forged).status_code == 401

    def test_token_without_expiry(self, api, method, path, body, role):
        payload = token_for(role)
        del payload["exp"]
        assert call(api, method, path, body, encode(payload)).status_code == 401


# ----- Rôles (403) -----------------------------------------------------------------------------
@pytest.mark.parametrize("method,path,body,role", ROUTES, ids=IDS)
def test_other_role_gets_403(api, method, path, body, role):
    other = "doctor" if role == "admin" else "admin"
    assert call(api, method, path, body, encode(token_for(other))).status_code == 403


@pytest.mark.parametrize("bad_role", [None, "", "superadmin", "ADMIN", "root"])
@pytest.mark.parametrize("method,path,body,role", ROUTES, ids=IDS)
def test_missing_or_unknown_role_gets_403(api, method, path, body, role, bad_role):
    assert call(api, method, path, body, encode(token_for(bad_role))).status_code == 403


def test_doctor_cannot_obtain_superset_token_and_superset_is_not_called(api, monkeypatch):
    stub = Stub()
    monkeypatch.setattr(superset_service, "get_client", lambda: stub)
    r = call(api, "post", "/v1/superset/guest-token", {"dashboard": "visite"}, encode(token_for("doctor")))
    assert r.status_code == 403 and stub.calls == 0


# ----- Aucun secret exposé ---------------------------------------------------------------------
def test_guest_token_response_has_only_expected_fields(api, monkeypatch):
    monkeypatch.setattr(superset_service, "get_client", lambda: Stub())
    r = call(api, "post", "/v1/superset/guest-token", {"dashboard": "visite"}, encode(token_for("admin")))
    assert r.status_code == 200
    assert set(r.json()) == {"dashboard_key", "dashboard_id", "token", "expires_at", "superset_domain"}
    assert r.headers["cache-control"] == "no-store"
    assert SECRET not in r.text and BACKEND_PASSWORD not in r.text


def test_errors_and_logs_never_contain_secrets(api, monkeypatch, env, caplog):
    monkeypatch.setattr(superset_service, "get_client",
                        lambda: Stub(SupersetAuthError(f"login refusé pour {BACKEND_PASSWORD}")))
    token = encode(token_for("admin"))
    with caplog.at_level(logging.DEBUG):
        r1 = call(api, "post", "/v1/superset/guest-token", {"dashboard": "visite"}, token)
        r2 = call(api, "post", "/v1/superset/guest-token", {"dashboard": "inconnu"}, token)
        call(api, "get", "/v1/superset/dashboards", None, "jeton.invalide.ici")
    assert (r1.status_code, r2.status_code) == (502, 404)
    audit = (env / "audit.jsonl").read_text(encoding="utf-8")
    for text in (r1.text, r2.text, audit):
        assert SECRET not in text and token not in text
    assert r1.text.count(BACKEND_PASSWORD) == 0 and BACKEND_PASSWORD not in audit
    assert token not in caplog.text and SECRET not in caplog.text
