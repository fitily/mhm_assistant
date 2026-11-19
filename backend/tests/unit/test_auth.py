"""Tests de l'authentification : hachage, connexion, jeton avec rôle, limitation des essais."""
import datetime as dt

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import current_principal, require_role
from app.core import passwords, security
from app.core.config import get_settings
from app.core.errors import ConfigurationError
from app.infrastructure.db.users import UserRecord
from app.main import create_app
from app.services import auth_service

SECRET = "s" * 48
PASSWORD = "correct-horse-1"


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("LOGIN_LOCK_MINUTES", "15")
    get_settings.cache_clear()
    auth_service.throttle.clear()
    yield
    get_settings.cache_clear()
    auth_service.throttle.clear()


@pytest.fixture
def accounts(monkeypatch):
    """Faux annuaire en mémoire (aucune base nécessaire)."""
    password_hash = passwords.hash_password(PASSWORD)
    data = {
        "medecin@mhm.org": UserRecord(1, "medecin@mhm.org", "Docteur Test", password_hash, "doctor", True),
        "admin@mhm.org": UserRecord(2, "admin@mhm.org", "Admin Test", password_hash, "admin", True),
        "ancien@mhm.org": UserRecord(3, "ancien@mhm.org", "Ancien", password_hash, "doctor", False),
    }
    monkeypatch.setattr(auth_service.users, "find_by_email", lambda email: data.get(email.lower()))
    monkeypatch.setattr(auth_service.users, "touch_last_login", lambda user_id: None)
    return data


@pytest.fixture
def client():
    return TestClient(create_app())


def login(client, username, password=PASSWORD):
    return client.post("/v1/auth/login", json={"username": username, "password": password})


def test_password_hash_roundtrip():
    password_hash = passwords.hash_password(PASSWORD)
    assert password_hash != PASSWORD
    assert passwords.verify_password(password_hash, PASSWORD)
    assert not passwords.verify_password(password_hash, "autre-mot-de-passe")


def test_verify_without_account_is_always_false():
    assert not passwords.verify_password(None, "mot-de-passe-factice")
    assert not passwords.verify_password("pas-un-hachage", PASSWORD)


def test_password_too_short_is_refused():
    with pytest.raises(ValueError):
        passwords.check_strength("court")


def test_login_returns_token_with_role(client, accounts):
    response = login(client, "medecin@mhm.org")
    body = response.json()

    assert response.status_code == 200
    assert body["user"] == {"email": "medecin@mhm.org", "name": "Docteur Test", "role": "doctor"}
    assert body["expires_in"] == 3600
    principal = security.decode_token(body["access_token"])
    assert (principal.user, principal.role) == ("medecin@mhm.org", "doctor")


def test_login_is_case_insensitive_on_email(client, accounts):
    assert login(client, "  Admin@MHM.org ").status_code == 200


@pytest.mark.parametrize("username", ["medecin@mhm.org", "inconnu@mhm.org", "ancien@mhm.org"])
def test_failed_login_gives_same_generic_error(client, accounts, username):
    response = login(client, username, "mauvais-mot-de-passe")

    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiant ou mot de passe incorrect."


def test_inactive_account_cannot_login_even_with_right_password(client, accounts):
    assert login(client, "ancien@mhm.org").status_code == 401


def test_too_many_failures_lock_the_account(client, accounts):
    for _ in range(3):
        assert login(client, "medecin@mhm.org", "faux-faux-faux").status_code == 401

    blocked = login(client, "medecin@mhm.org")  # même avec le bon mot de passe

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert login(client, "admin@mhm.org").status_code == 200  # un autre compte n'est pas touché


def test_successful_login_resets_failure_counter(client, accounts):
    for _ in range(2):
        login(client, "medecin@mhm.org", "faux-faux-faux")
    assert login(client, "medecin@mhm.org").status_code == 200
    for _ in range(2):
        assert login(client, "medecin@mhm.org", "faux-faux-faux").status_code == 401


def test_throttle_releases_after_the_window():
    now = [0.0]
    throttle = auth_service.LoginThrottle(clock=lambda: now[0])
    for _ in range(3):
        throttle.record_failure("a@mhm.org")
    assert throttle.blocked_for("a@mhm.org") > 0

    now[0] = 15 * 60 + 1

    assert throttle.blocked_for("a@mhm.org") == 0


def test_user_database_down_returns_503(client, monkeypatch):
    def broken(email):
        raise ConfigurationError("APP_PASSWORD est requis")

    monkeypatch.setattr(auth_service.users, "find_by_email", broken)

    assert login(client, "medecin@mhm.org").status_code == 503


def test_me_requires_a_token(client):
    assert client.get("/v1/auth/me").status_code == 401


def test_me_returns_the_role_from_the_token(client, accounts):
    token = login(client, "admin@mhm.org").json()["access_token"]

    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.json() == {"email": "admin@mhm.org", "name": "Admin Test", "role": "admin"}


def _role_app():
    app = FastAPI()

    @app.get("/admin-only")
    def admin_only(principal=Depends(require_role("admin"))):
        return {"user": principal.user}

    @app.get("/anyone")
    def anyone(principal=Depends(current_principal)):
        return {"role": principal.role}

    return TestClient(app)


def _token(**claims):
    payload = {"sub": "x@mhm.org", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)}
    payload.update(claims)
    return jwt.encode({k: v for k, v in payload.items() if v is not None}, SECRET, algorithm="HS256")


@pytest.mark.parametrize(("role", "status_code"), [("admin", 200), ("doctor", 403), (None, 403)])
def test_require_role_checks_the_role(role, status_code):
    response = _role_app().get("/admin-only", headers={"Authorization": f"Bearer {_token(role=role)}"})

    assert response.status_code == status_code


def test_unknown_role_in_token_is_ignored():
    response = _role_app().get("/anyone", headers={"Authorization": f"Bearer {_token(role='root')}"})

    assert response.json() == {"role": None}


def test_expired_token_is_refused():
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)

    response = _role_app().get("/anyone", headers={"Authorization": f"Bearer {_token(exp=past)}"})

    assert response.status_code == 401


def test_token_signed_with_another_secret_is_refused():
    forged = jwt.encode({"sub": "x", "role": "admin", "exp": 9999999999}, "z" * 48, algorithm="HS256")

    assert _role_app().get("/anyone", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_token_without_expiry_is_refused():
    eternal = jwt.encode({"sub": "x", "role": "admin"}, SECRET, algorithm="HS256")

    assert _role_app().get("/anyone", headers={"Authorization": f"Bearer {eternal}"}).status_code == 401


def test_missing_token_is_refused():
    assert _role_app().get("/anyone").status_code == 401


def test_auth_disabled_uses_dev_role(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.setenv("DEV_ROLE", "doctor")
    get_settings.cache_clear()

    assert _role_app().get("/anyone").json() == {"role": "doctor"}


def test_short_secret_refuses_to_issue_tokens(client, accounts, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "trop-court")
    get_settings.cache_clear()

    assert login(client, "medecin@mhm.org").status_code == 500
