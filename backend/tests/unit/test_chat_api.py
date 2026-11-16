from fastapi.testclient import TestClient

from app.api import chat
from app.api.deps import current_user
from app.domain.models import AnswerResult
from app.main import create_app


def test_chat_stream_emits_waiting_message_tokens_and_complete_response(monkeypatch):
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
        "/v1/chat/stream", json={"question": "question", "mode": "DOCS"})
    events = response.text

    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in events
    assert "IA'mbovo> Recherche dans les documents…" in events
    assert events.index("event: status") < events.index("event: token")
    assert events.count("event: token") == 2
    assert "event: complete" in events
    assert memory.saved == ("question", "Réponse en direct.")
