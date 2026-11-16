import pytest
from fastapi.testclient import TestClient

from app.api import chat
from app.api.deps import current_user
from app.domain.models import AnswerResult
from app.main import create_app


@pytest.mark.parametrize(("question", "expected_status"), [
    ("Find information about HIV", "IA'mbovo> Searching the documents…"),
    ("C'est quoi le VIH ?", "IA'mbovo> Recherche dans les documents…"),
    ("Inona no atao hoe VIH?", "IA'mbovo> Mikaroka ao amin'ny antontan-taratasy…"),
])
def test_chat_stream_emits_language_matched_status_and_tokens(
        monkeypatch, question, expected_status):
    class Memory:
        history = []

        def add(self, question, answer):
            self.saved = (question, answer)

    memory = Memory()
    monkeypatch.setattr(chat.sessions, "get", lambda key: memory)

    def answer(question, **kwargs):
        kwargs["on_docs_wait"]()
        kwargs["on_docs_token"]("Réponse ")
        kwargs["on_docs_token"]("en direct.")
        return AnswerResult("Réponse en direct.", "DOCS")

    monkeypatch.setattr(chat.chat_service, "answer", answer)
    app = create_app()
    app.dependency_overrides[current_user] = lambda: "test"

    response = TestClient(app).post(
        "/v1/chat/stream", json={"question": question, "mode": "DOCS"})
    events = response.text

    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in events
    assert expected_status in events
    assert events.index("event: status") < events.index("event: token")
    assert events.count("event: token") == 2
    assert "event: complete" in events
    assert memory.saved == (question, "Réponse en direct.")
