"""Commandes de tableau de bord dans le chat : réservées à l'admin, sans IA, avec une action pour l'interface."""
import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_principal
from app.core.config import get_settings
from app.core.errors import ConfigurationError
from app.core.security import Principal
from app.domain.models import AnswerResult
from app.main import create_app
from app.services import chat_service

UUID_A = "b973604e-c78d-47ce-8fdf-876722c1aaed"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    """Ni LLM, ni base : si une commande de dashboard atteignait le routage normal, le test échouerait."""
    calls = {"audit": []}

    def boom(*a, **k):
        raise AssertionError("le routage normal ne doit pas être appelé pour une commande de dashboard")

    monkeypatch.setattr(chat_service, "audit", lambda *args: calls["audit"].append(args))
    monkeypatch.setattr(chat_service.router, "route", boom)
    monkeypatch.setattr(chat_service.router, "rewrite_followup", boom)
    get_settings.cache_clear()
    yield calls
    get_settings.cache_clear()


def test_admin_opens_a_dashboard(isolated):
    result = chat_service.answer("Montre-moi le tableau de bord des visites", role="admin", user="a@mhm.org")
    assert result.mode == "DASHBOARD"
    assert result.action == {"type": "open_dashboard", "dashboard": "visite", "title": "AI-assistant-dashboard"}
    assert "AI-assistant-dashboard" in result.text
    assert UUID_A not in str(result.action)  # jamais d'UUID dans l'ordre envoyé à l'interface
    assert isolated["audit"][0][3] == "dashboard_open:visite"


def test_admin_switch_close_previous(isolated):
    assert chat_service.answer("Passe au dashboard médical", role="admin").action["dashboard"] == "medicale"
    assert chat_service.answer("Close the dashboard", role="admin").action == {"type": "close_dashboard"}
    assert chat_service.answer("Go back to the previous dashboard", role="admin").action == {"type": "previous_dashboard"}


def test_answer_follows_the_language_of_the_question():
    assert chat_service.answer("Show me the visits dashboard", role="admin").text.startswith("Opening")
    assert chat_service.answer("Ouvre le tableau de bord des visites", role="admin").text.startswith("J'ouvre")


def test_ambiguous_request_asks_without_action():
    result = chat_service.answer("Montre-moi un tableau de bord", role="admin")
    assert result.action is None
    assert "AI-assistant-dashboard" in result.text and "HMH_Medical_Dashboard" in result.text


def test_doctor_is_refused_and_gets_no_action(isolated):
    result = chat_service.answer("Ouvre le tableau de bord des visites", role="doctor", user="m@mhm.org")
    assert result.action is None
    assert "médecin" in result.text
    assert isolated["audit"][0][3] == "forbidden:DASHBOARD"


def test_unknown_role_is_refused():
    assert chat_service.answer("Open the visits dashboard", role="root").action is None


def test_statistical_question_about_dashboard_is_not_hijacked(monkeypatch):
    seen = {}
    monkeypatch.undo()  # retire les pièges : ici le routage normal DOIT être utilisé
    monkeypatch.setattr(chat_service, "audit", lambda *a: None)
    monkeypatch.setattr(chat_service.router, "route", lambda q, h=None: seen.setdefault("routed", q) and chat_service.router.Route("sql", q))
    monkeypatch.setattr(chat_service, "_tabular", lambda *a, **k: AnswerResult("Il y a 3 visites.", "SQL"))
    result = chat_service.answer("Combien de visites y a-t-il dans le tableau de bord ?", role="admin")
    assert "routed" in seen and result.mode == "SQL" and result.action is None


def test_forced_mode_skips_dashboard_detection(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(chat_service, "audit", lambda *a: None)
    monkeypatch.setattr(chat_service.router, "rewrite_followup", lambda q, h=None: q)
    monkeypatch.setattr(chat_service, "_tabular", lambda *a, **k: AnswerResult("Voici.", "SQL"))
    result = chat_service.answer("Ouvre le tableau de bord des visites", forced="SQL", role="admin")
    assert result.mode == "SQL" and result.action is None


def test_broken_catalog_never_breaks_the_chat(monkeypatch):
    def broken():
        raise ConfigurationError("illisible")
    monkeypatch.setattr(chat_service, "get_catalog", broken)
    assert chat_service._dashboard_command("Ouvre le dashboard", "fr", "admin") is None


# ----- API : l'action arrive bien dans la réponse JSON --------------------------------------
@pytest.mark.parametrize("role,has_action", [("admin", True), ("doctor", False)])
def test_api_returns_action_only_for_admin(role, has_action):
    app = create_app()
    app.dependency_overrides[current_principal] = lambda: Principal("u@mhm.org", role)
    r = TestClient(app).post("/v1/chat", json={"question": "Open the visits dashboard"})
    assert r.status_code == 200
    body = r.json()
    assert (body["action"] is not None) is has_action
    if has_action:
        assert body["action"]["dashboard"] == "visite" and body["mode"] == "DASHBOARD"
