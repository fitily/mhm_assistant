"""Droits par rôle : un médecin n'a que les documents, un administrateur que les statistiques."""
import datetime as dt

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain import permissions
from app.domain.models import AnswerResult
from app.main import create_app
from app.services import chat_service

SECRET = "s" * 48
STATS_FR = "Combien de patients par district ?"
DOCS_FR = "Quels sont les symptômes du paludisme ?"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    """Aucune base, aucun LLM, aucun fichier d'audit : on teste seulement les droits."""
    calls = {"audit": [], "sql": 0, "docs": 0}

    def sql(*args, **kwargs):
        calls["sql"] += 1
        return AnswerResult("Il y a 3 patients.", "SQL")

    def docs(*args, **kwargs):
        calls["docs"] += 1
        return AnswerResult("Voici ce que disent les documents.", "DOCS")

    monkeypatch.setattr(chat_service, "audit", lambda *args: calls["audit"].append(args))
    monkeypatch.setattr(chat_service, "_tabular", sql)
    monkeypatch.setattr(chat_service, "_docs", docs)
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", SECRET)
    get_settings.cache_clear()
    yield calls
    get_settings.cache_clear()


@pytest.mark.parametrize(("role", "mode", "expected"), [
    ("doctor", "DOCS", True), ("doctor", "CHAT", True), ("doctor", "SQL", False),
    ("admin", "SQL", True), ("admin", "CHAT", True), ("admin", "DOCS", False),
    (None, "CHAT", False), ("root", "SQL", False), ("doctor", "DASHBOARD", False), ("admin", "DASHBOARD", True),
])
def test_is_allowed(role, mode, expected):
    assert permissions.is_allowed(role, mode) is expected


def test_doctor_cannot_get_statistics(isolated):
    result = chat_service.answer(STATS_FR, role="doctor", user="medecin@mhm.org")

    assert result.mode == "CHAT"
    assert "pas disponibles pour votre profil (médecin)" in result.text
    assert "contactez un administrateur" in result.text
    assert isolated["sql"] == 0
    assert isolated["audit"][0][3] == "forbidden:SQL"  # l'essai est tracé dans le journal d'audit


def test_admin_cannot_get_document_answers(isolated):
    result = chat_service.answer(DOCS_FR, role="admin", user="admin@mhm.org")

    assert result.mode == "CHAT"
    assert "pour votre profil (administrateur)" in result.text
    assert isolated["docs"] == 0
    assert isolated["audit"][0][3] == "forbidden:DOCS"


def test_refusal_follows_the_language_of_the_question():
    result = chat_service.answer("How many patients per district?", role="doctor")

    assert result.text.startswith("Statistics are not available for your profile")


def test_each_role_keeps_its_own_source(isolated):
    assert chat_service.answer(STATS_FR, role="admin").mode == "SQL"
    assert chat_service.answer(DOCS_FR, role="doctor").mode == "DOCS"
    assert (isolated["sql"], isolated["docs"]) == (1, 1)


@pytest.mark.parametrize("role", ["doctor", "admin"])
def test_greeting_is_allowed_for_both_roles(role):
    result = chat_service.answer("Bonjour", role=role)

    assert result.mode == "CHAT"
    assert "iA'mbovo" in result.text


@pytest.mark.parametrize(("role", "forced"), [("doctor", "SQL"), ("admin", "DOCS")])
def test_forced_mode_cannot_bypass_the_role(isolated, role, forced):
    result = chat_service.answer("Combien de patients ?", role=role, forced=forced)

    assert result.audit_stage == f"forbidden:{forced}"
    assert (isolated["sql"], isolated["docs"]) == (0, 0)


def test_no_role_means_no_restriction_for_local_tools(isolated):
    assert chat_service.answer(STATS_FR).mode == "SQL"  # ex. le CLI sur la machine de l'opérateur


def test_unknown_role_is_refused_even_for_statistics(isolated):
    result = chat_service.answer(STATS_FR, role="root")

    assert result.audit_stage == "forbidden:SQL"
    assert isolated["sql"] == 0


# --- Au niveau de l'API (vrai jeton, vraies routes) ---

def _headers(role):
    claims = {"sub": "u@mhm.org", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)}
    if role:
        claims["role"] = role
    token = jwt.encode(claims, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(create_app())


def test_api_doctor_is_refused_statistics(client, isolated):
    response = client.post("/v1/chat", json={"question": STATS_FR}, headers=_headers("doctor"))

    assert response.status_code == 200
    assert response.json()["mode"] == "CHAT"
    assert "médecin" in response.json()["text"]
    assert isolated["sql"] == 0


def test_api_admin_gets_statistics(client):
    response = client.post("/v1/chat", json={"question": STATS_FR}, headers=_headers("admin"))

    assert response.json()["mode"] == "SQL"


def test_api_doctor_gets_documents(client):
    response = client.post("/v1/chat", json={"question": DOCS_FR}, headers=_headers("doctor"))

    assert response.json()["mode"] == "DOCS"


def test_api_forced_mode_is_still_checked(client, isolated):
    response = client.post("/v1/chat", json={"question": "Combien ?", "mode": "SQL"},
                           headers=_headers("doctor"))

    assert response.json()["mode"] == "CHAT"
    assert isolated["sql"] == 0


def test_api_token_without_role_is_forbidden(client):
    assert client.post("/v1/chat", json={"question": "Bonjour"}, headers=_headers(None)).status_code == 403


def test_api_requires_a_token(client):
    assert client.post("/v1/chat", json={"question": "Bonjour"}).status_code == 401


def test_api_stream_also_applies_the_role(client, isolated):
    response = client.post("/v1/chat/stream", json={"question": STATS_FR}, headers=_headers("doctor"))

    assert "event: complete" in response.text
    assert "médecin" in response.text
    assert "event: error" not in response.text
    assert isolated["sql"] == 0


def test_api_stream_refuses_token_without_role(client):
    response = client.post("/v1/chat/stream", json={"question": "Bonjour"}, headers=_headers(None))

    assert response.status_code == 403
