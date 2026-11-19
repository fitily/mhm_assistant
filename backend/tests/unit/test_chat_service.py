from app.domain.models import AnswerResult
from app.services import chat_service


def test_sql_response_uses_french_natural_summary_and_result_number(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "MHM compte 47\u202f597 patients.")

    answer = chat_service._compose(
        "Combien de patients chez MHM ?", "SELECT COUNT(*)", ["total_patients"],
        [(47597,)], [], [], language="fr")

    assert "MHM compte 47\u202f597 patients." == answer
    assert "total_patients" not in answer


def test_llm_table_is_removed_before_code_formats_rows(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "Répartition calculée :\n| Age | Count |\n|---|---|\n|18|2|")

    answer = chat_service._compose(
        "Admissions par âge", "SELECT ...", ["age_group", "admissions"],
        [("18-23", 2)], [], [], language="fr")

    assert answer.startswith("Répartition calculée :")
    assert answer.count("Tranche d'âge") == 1
    assert "Age | Count" not in answer


def test_scalar_result_is_shown_if_summary_omits_its_value(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "Des admissions ont été enregistrées.")

    answer = chat_service._compose(
        "Combien d'admissions ?", "SELECT COUNT(*)", ["total_admissions"],
        [(0,)], ["Vérifiez les filtres."], [], language="fr")

    assert answer.startswith("Le nombre correspondant est 0.")
    assert "À noter : Vérifiez les filtres." in answer


def test_summary_cannot_hide_a_positive_scalar_result(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "Il n'y a pas de femmes.")

    answer = chat_service._compose(
        "Combien de femmes ?", "SELECT COUNT(*)", ["admissions"],
        [(1,)], [], [], language="fr")

    assert "Il n'y a pas de femmes." not in answer
    assert "Le nombre correspondant est 1." == answer
    assert "Admissions" not in answer


def test_chat_prompt_enforces_detected_language(monkeypatch):
    seen = []

    def complete(prompt, *args, **kwargs):
        seen.append(prompt)
        return "I can help with that request."

    monkeypatch.setattr(chat_service.ollama, "complete", complete)

    result = chat_service._general("Hello", "Hello", "en", [])

    assert result.mode == "CHAT"
    assert "Answer ONLY in English" in seen[0]


def test_chat_prompt_uses_french_and_malagasy_for_current_message(monkeypatch):
    observed = []
    responses = {
        "French": "Je peux vous aider avec cette question.",
        "Malagasy": "Afaka manampy anao amin'ity fanontaniana ity aho.",
    }

    def complete(prompt, *args, **kwargs):
        observed.append(prompt)
        language = next(name for name in responses if f"Answer ONLY in {name}" in prompt)
        return responses[language]

    monkeypatch.setattr(chat_service.ollama, "complete", complete)

    french = chat_service._general("Qui êtes-vous ?", "Qui êtes-vous ?", "fr", [])
    malagasy = chat_service._general("Iza ianao?", "Iza ianao?", "mg", [])

    assert "Je peux vous aider" in french.text
    assert "Afaka manampy anao" in malagasy.text
    assert "Answer ONLY in French" in observed[0]
    assert "Answer ONLY in Malagasy" in observed[1]


def test_conversation_summary_prompt_is_short_and_language_specific(monkeypatch):
    seen = []
    monkeypatch.setattr(
        chat_service.ollama,
        "complete",
        lambda prompt, *args, **kwargs: seen.append(prompt) or "The conversation covered patients.",
    )

    result = chat_service._general(
        "Summarize our conversation", "Summarize our conversation", "en",
        [("Bonjour", "Nous avons parlé des patients.")])

    assert result.mode == "CHAT"
    assert "2 or 3 sentences in English" in seen[0]
    assert "Bonjour" in seen[0]


def test_chat_translates_a_wrong_language_completion_to_current_message_language(monkeypatch):
    calls = []

    def complete(prompt, *args, **kwargs):
        calls.append(prompt)
        if "Answer ONLY in English" in prompt:
            return "Bonjour, je suis iA'mbovo, l'assistant IA de MHM Ambovo."
        return "Hello, I'm iA'mbovo, the AI assistant at MHM Ambovo."

    monkeypatch.setattr(chat_service.ollama, "complete", complete)

    result = chat_service._general("Who are you?", "Who are you?", "en", [])

    assert "Hello, I'm iA'mbovo" in result.text
    assert len(calls) == 2
    assert "Translate the answer below faithfully into English" in calls[1]


def test_english_identity_question_stays_english_end_to_end(monkeypatch):
    replies = iter([
        "Bonjour, je suis iA'mbovo, l'assistant IA de MHM Ambovo.",
        "Hello, I'm iA'mbovo, the AI assistant at MHM Ambovo.",
    ])
    monkeypatch.setattr(
        chat_service.ollama,
        "complete",
        lambda *args, **kwargs: next(replies),
    )
    monkeypatch.setattr(chat_service, "audit", lambda *args: None)

    result = chat_service.answer("who are you?")

    assert result.text.startswith("Hello, I'm iA'mbovo")
    assert "Bonjour" not in result.text


def test_sql_summary_and_table_labels_follow_requested_language(monkeypatch):
    prompts = []

    def complete(prompt, *args, **kwargs):
        prompts.append(prompt)
        if "Translate the answer below faithfully into English" in prompt:
            return "There were 2 patients."
        return "Il y avait 2 patients."

    monkeypatch.setattr(chat_service.ollama, "complete", complete)

    answer = chat_service._compose(
        "How many patients?", "SELECT count(*)", ["total_patients"], [(2,)], [], [],
        language="en")

    assert answer == "There were 2 patients."
    assert "Patients: 2" in prompts[0]


def test_answer_rejects_greeting_only_completion(monkeypatch):
    monkeypatch.setattr(chat_service, "audit", lambda *args: None)
    monkeypatch.setattr(
        chat_service.router,
        "route",
        lambda *args: chat_service.router.Route("chat", "question autonome"),
    )
    monkeypatch.setattr(
        chat_service,
        "_general",
        lambda *args: AnswerResult("Bonjour !", "CHAT"),
    )

    result = chat_service.answer("Parle-moi de cette organisation")

    assert result.mode == "CHAT"
    assert result.text.startswith("Je n'ai pas pu formuler une réponse utile.")
