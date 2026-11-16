import json
from pathlib import Path

import pytest

from app.api import chat as chat_api
from app.core.config import ASSISTANT_NAME
from app.domain import router
from app.domain.conversation import ConversationMemory
from app.schemas.chat import ClearRequest


@pytest.mark.parametrize(("question", "expected"), [
    ("Combien de patients ?", "sql"),
    ("Combien de femmes ont consulté ?", "sql"),
    ("Les symptômes du SIDA", "docs"),
    ("Quelle est la définition de la tuberculose ?", "docs"),
    ("Que signifie le VIH ?", "docs"),
    ("Qui es-tu ?", "chat"),
    ("Merci", "chat"),
    ("Est-ce que je peux poser des questions sur le VIH ?", "chat"),
    ("Combien de patients ?", "sql"),
    ("what does HIV stand for", "docs"),
    ("c'est quoi le SIDA", "docs"),
    ("résume notre conversation", "chat"),
    ("Merci, combien de patients ?", "sql"),
    ("Bonjour", "chat"),
])
def test_deterministic_routes_do_not_call_llm(monkeypatch, question, expected):
    def unexpected(*args, **kwargs):
        raise AssertionError("Le LLM ne doit servir qu'en dernier recours.")

    monkeypatch.setattr(router.ollama, "complete", unexpected)

    assert router.route(question).name == expected


def test_followup_is_rewritten_before_deterministic_route(monkeypatch):
    prompts = []

    def complete(prompt, **kwargs):
        prompts.append(prompt)
        return json.dumps({"question": "Que signifie le total des fiches patients du résultat précédent ?"})

    monkeypatch.setattr(router.ollama, "complete", complete)
    history = [("Combien de patients ?", "Il y a 47 597 patients.")]

    result = router.route("Que veut dire total patients ?", history)

    assert result.name == "chat"
    assert "résultat précédent" in result.question
    assert len(prompts) == 1
    assert "47 597" in prompts[0]


def test_standalone_short_request_is_not_rewritten_as_a_followup(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Une requête autonome ne doit pas être réécrite.")

    monkeypatch.setattr(router.ollama, "complete", unexpected)

    assert router.rewrite_followup(
        "Une demande inhabituelle", [("question précédente", "réponse")]) == "Une demande inhabituelle"


def test_identity_and_capability_questions_are_chat(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Le routage ne doit pas appeler le LLM.")

    monkeypatch.setattr(router.ollama, "complete", unexpected)

    for question in ("Qui es-tu ?", "Que peux-tu faire ?",
                     "Est-ce que je peux poser des questions sur le VIH ?"):
        assert router.route(question).name == "chat"


def test_no_legacy_mode_exists_in_application_code():
    legacy_mode = "".join(("CAPABILI", "TIES"))
    app = Path(__file__).resolve().parents[2] / "app"

    assert all(legacy_mode not in path.read_text(encoding="utf-8")
               for path in app.rglob("*.py"))


def test_chat_refuses_medical_content_without_documents():
    assert "documents chargés" in router.guard_general(
        "Le VIH se transmet ainsi.", "Explique le VIH.")
    assert router.guard_general("Je peux vous aider.", "Bonjour") == "Je peux vous aider."


def test_chat_allows_capability_reply_about_medical_documents():
    answer = "Yes, I can answer questions about HIV using the loaded documents."

    assert router.guard_general(
        answer, "Can I ask questions about HIV?") == answer


def test_chat_never_claims_to_lack_data_access():
    result = router.guard_general(
        "I won't have access to real-time or personal data.", "Can I ask about HIV?")

    assert "loaded documents" in result


def test_conversation_summary_can_report_topics_from_history():
    summary = "We discussed HIV symptoms and how to search the loaded documents."

    assert router.guard_general(
        summary, "résume notre conversation",
        [("Quels sont les symptômes du VIH ?", "Sources : guide.pdf - page 1")]) == summary


@pytest.mark.parametrize("text", [
    "", "Bonjour !", "Hello, how can I help?",
    "Je n'ai pas accès aux bases de données.",
    ("Bonjour ! Je suis ravi de vous aider avec vos questions statistiques sur MHM. "
     "Je vais faire de mon mieux pour vous fournir des réponses claires et concises. "
     "N'hésitez pas à me poser vos questions, je suis là pour vous aider !"),
    ("Bonjour ! Je suis ravi de vous aider. Je vais faire de mon mieux pour vous aider. "
     "N'hésitez pas à me poser vos questions, et je ferai de mon mieux pour vous aider. "
     "Qu'est-ce que vous souhaitez savoir sur MHM ?"),
])
def test_empty_or_greeting_only_responses_are_not_useful(text):
    assert not router.has_useful_content(text)


def test_substantive_text_is_useful():
    assert router.has_useful_content("La demande concerne les statistiques de MHM.")


def test_short_correct_document_answer_is_useful():
    assert router.has_useful_content("HIV means Human Immunodeficiency Virus.")


def test_language_is_detected_from_each_current_question():
    assert router.detect_lang("HIV in Saudi Arabia") == "en"
    assert router.detect_lang("do you have any clue about HIV in Saudi Arabia") == "en"
    assert router.detect_lang("c'est quoi le VIH") == "fr"
    assert router.detect_lang("who are you?") == "en"
    assert router.detect_lang("Bonjour") == "fr"
    assert router.detect_lang("Le VIH") == "fr"
    assert router.detect_lang("Iza ianao?") == "mg"
    assert router.detect_lang("Inona no atao hoe VIH?") == "mg"
    assert router.detect_lang("Ny VIH") == "mg"
    assert router.detect_lang("HIV") == "en"


def test_language_changes_with_each_message_and_does_not_follow_history():
    messages = [
        ("Who are you?", "en"),
        ("Qui es-tu ?", "fr"),
        ("Iza ianao?", "mg"),
    ]

    assert [router.detect_lang(message) for message, _ in messages] == [
        language for _, language in messages]


def test_fixed_greetings_follow_the_detected_language():
    assert router.quick_reply("Hello")[1].startswith("Hello,")
    assert router.quick_reply("Bonjour")[1].startswith("Bonjour,")
    assert router.quick_reply("Salama")[1].startswith("Salama,")


def test_conversation_keeps_last_ten_exchanges():
    memory = ConversationMemory()
    for i in range(12):
        memory.add(f"question {i}", f"réponse {i}")

    assert len(memory.history) == 10
    assert memory.history[0] == ("question 2", "réponse 2")
    memory.clear()
    assert memory.history == []


def test_api_clear_empties_only_the_requested_session():
    memory = chat_api.sessions.get("test-user:clear-test")
    memory.add("question", "answer")

    chat_api.clear(ClearRequest(session_id="clear-test"), "test-user")

    assert memory.history == []


def test_api_response_uses_assistant_sender(monkeypatch):
    from app.domain.models import AnswerResult
    from app.schemas.chat import ChatRequest

    monkeypatch.setattr(chat_api.chat_service, "answer",
                        lambda *args, **kwargs: AnswerResult("Bonjour.", "CHAT"))

    response = chat_api.chat(ChatRequest(question="Bonjour"), user="test-user:sender")

    assert response.sender == ASSISTANT_NAME
    assert response.mode == "CHAT"
