from app.domain.models import AnswerResult
from app.services import chat_service


def test_sql_response_uses_french_natural_summary_and_result_number(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "MHM compte 47\u202f597 patients.")

    answer = chat_service._compose(
        "Combien de patients chez MHM ?", "SELECT COUNT(*)", ["total_patients"],
        [(47597,)], [], [])

    assert "MHM compte 47\u202f597 patients." == answer
    assert "total_patients" not in answer


def test_llm_table_is_removed_before_code_formats_rows(monkeypatch):
    monkeypatch.setattr(
        chat_service.ollama, "complete",
        lambda *args, **kwargs: "Répartition calculée :\n| Age | Count |\n|---|---|\n|18|2|")

    answer = chat_service._compose(
        "Admissions par âge", "SELECT ...", ["age_group", "admissions"],
        [("18-23", 2)], [], [])

    assert answer.startswith("Répartition calculée :")
    assert answer.count("Tranche d'âge") == 1
    assert "Age | Count" not in answer


def test_scalar_result_is_shown_if_summary_omits_its_value(monkeypatch):
    monkeypatch.setattr(chat_service.ollama, "complete",
                        lambda *args, **kwargs: "Des admissions ont été enregistrées.")

    answer = chat_service._compose(
        "Combien d'admissions ?", "SELECT COUNT(*)", ["total_admissions"],
        [(0,)], ["Vérifiez les filtres."], [])

    assert answer.startswith("Le nombre correspondant est 0.")
    assert "À noter : Vérifiez les filtres." in answer


def test_summary_cannot_hide_a_positive_scalar_result(monkeypatch):
    monkeypatch.setattr(chat_service.ollama, "complete",
                        lambda *args, **kwargs: "Il n'y a pas de femmes.")

    answer = chat_service._compose(
        "Combien de femmes ?", "SELECT COUNT(*)", ["admissions"],
        [(1,)], [], [])

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
    assert "Réponds UNIQUEMENT en anglais," in seen[0]


def test_conversation_summary_prompt_is_short_and_language_specific(monkeypatch):
    seen = []
    monkeypatch.setattr(chat_service.ollama, "complete",
                        lambda prompt, *args, **kwargs: seen.append(prompt) or "The conversation covered patients.")

    result = chat_service._general(
        "Summarize our conversation", "Summarize our conversation", "en",
        [("Bonjour", "Nous avons parlé des patients.")])

    assert result.mode == "CHAT"
    assert "2 ou 3 phrases dans la langue anglais" in seen[0]
    assert "Bonjour" in seen[0]


def test_docs_prompt_enforces_detected_language(monkeypatch):
    seen = []
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : contexte", [(0.8, "guide.pdf - page 1")]))

    def stream(prompt, *args, **kwargs):
        seen.append(prompt)
        return "The excerpt says this."

    monkeypatch.setattr(chat_service.ollama, "stream", stream)

    history = [("Bonjour", "Je peux vous aider.")]
    result = chat_service._docs("What is in the document?", "en", history)

    assert result.mode == "DOCS"
    assert "uniquement en anglais" in seen[0]
    assert "Keep the answer concise" in seen[0]
    assert "Bonjour" in seen[0]


def test_short_document_answer_is_not_rejected(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : HIV stands for Human Immunodeficiency Virus.",
                                       [(0.7, "guide.pdf - page 2")]))
    monkeypatch.setattr(chat_service.ollama, "stream",
                        lambda *args, **kwargs: "HIV means Human Immunodeficiency Virus.")

    result = chat_service._docs("What does HIV stand for?", "en", [])

    assert result.text.startswith("HIV means Human Immunodeficiency Virus.")
    assert "guide.pdf - page 2" in result.text


def test_docs_streams_with_wait_message_and_short_generation_settings(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : contexte", [(0.8, "guide.pdf - page 1")]))
    calls = []
    events = []

    def stream(prompt, **kwargs):
        calls.append(kwargs)
        kwargs["emit"]("Réponse ")
        kwargs["emit"]("documentée.")
        return "Réponse documentée."

    monkeypatch.setattr(chat_service.ollama, "stream", stream)

    result = chat_service._docs(
        "question", "fr", [], on_docs_wait=lambda: events.append("wait"),
        on_docs_token=events.append)

    assert events == ["wait", "Réponse ", "documentée."]
    assert calls[0]["predict"] == 200
    assert calls[0]["num_ctx"] == 4096
    assert calls[0]["stage"] == "génération DOCS"
    assert result.text.startswith("Réponse documentée.")


def test_research_prompt_and_stream_guard_separate_knowledge_and_attitudes(monkeypatch):
    context = (
        "EXTRAITS :\n[study.pdf - page 4]\n"
        "[RAG section=results type=prose]\n"
        "Knowledge was correlated with age. Attitudes were measured separately. "
        "Awareness was 60%.")
    monkeypatch.setattr(
        chat_service, "get_doc_context",
        lambda *args: (context, [(0.8, "study.pdf - page 4")]))
    prompt_seen = []
    emitted = []
    reply = ("Knowledge and attitudes were significantly correlated. "
             "The study reported 60% awareness.")

    def stream(prompt, **kwargs):
        prompt_seen.append(prompt)
        kwargs["emit"]("Knowledge and attitudes were significantly correlated. ")
        kwargs["emit"]("The study reported 60% awareness.")
        return reply

    monkeypatch.setattr(chat_service.ollama, "stream", stream)
    result = chat_service._docs(
        "Summarize the findings", "en", [], on_docs_token=emitted.append)
    streamed = "".join(emitted)

    assert "Keep knowledge scores separate from attitudes" in prompt_seen[0]
    assert "the authors report" in prompt_seen[0].lower()
    assert "significantly correlated" not in streamed
    assert "do not state whether those measures are associated" in streamed
    assert "60% awareness" in streamed
    assert "do not state whether those measures are associated" in result.text
    assert "60% awareness" in result.text


def test_knowledge_attitude_link_is_allowed_when_source_explicitly_reports_it():
    context = (
        "[RAG section=results type=prose]\n"
        "The correlation between HIV transmission knowledge and attitudes was significant.")

    assert chat_service._guard_research_claims(
        "HIV transmission knowledge and attitudes were correlated.", context, "en"
    ) == "HIV transmission knowledge and attitudes were correlated."


def test_unsupported_negative_knowledge_attitude_claim_is_not_inferred():
    context = (
        "[RAG section=results type=prose]\n"
        "Knowledge was correlated with age. Attitudes were measured separately.")

    guarded = chat_service._guard_research_claims(
        "There was no correlation between knowledge and attitudes.", context, "en")

    assert "no correlation between knowledge and attitudes" not in guarded.lower()
    assert "do not state whether those measures are associated" in guarded


def test_unsupported_research_percentage_is_removed():
    context = (
        "[RAG section=results type=table table=2]\n"
        "Blood transmission awareness was 92.6%. Pregnancy transmission awareness was 60.3%.")

    guarded = chat_service._guard_research_percentages(
        "Blood transmission awareness was 92.6%. Pregnancy transmission awareness was 0%.",
        context, "en")

    assert "92.6%" in guarded
    assert "0%" not in guarded


def test_document_answer_is_translated_to_question_language(monkeypatch):
    calls = []
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : contexte",
                                       [(0.8, "guide.pdf - page 1")]))

    def complete(prompt, *args, **kwargs):
        calls.append(prompt)
        return "Yes, the excerpts discuss HIV."

    monkeypatch.setattr(
        chat_service.ollama, "stream",
        lambda *args, **kwargs: "Oui, les extraits parlent du VIH.")
    monkeypatch.setattr(chat_service.ollama, "complete", complete)

    result = chat_service._docs("Do you know about HIV?", "en", [("Bonjour", "Merci.")])

    assert result.text.startswith("Yes, the excerpts discuss HIV.")
    assert len(calls) == 1
    assert "anglais" in calls[0]
    assert "EXTRAITS : contexte" not in calls[0]
    assert result.text.count("Sources :") == 1


def test_document_generation_error_still_shows_retrieved_sources(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS :\n[guide.pdf - page 1]\nExtrait utile du document.\n",
                                       [(0.8, "guide.pdf - page 1")]))

    def fail(*args, **kwargs):
        raise RuntimeError("local model unavailable")

    monkeypatch.setattr(chat_service.ollama, "stream", fail)

    result = chat_service._docs("What is in this document?", "en", [])

    assert "not available" in result.text
    assert "Sources :" not in result.text
    assert "guide.pdf - page 1" in result.text
    assert "Extrait utile du document." in result.text
    assert result.sources == ()


def test_document_generation_timeout_uses_timeout_message_and_excerpts(monkeypatch):
    monkeypatch.setattr(
        chat_service, "get_doc_context",
        lambda *args: (
            "EXTRAITS :\n[guide.pdf - page 1]\n"
            "[RAG section=results type=table table=2]\n"
            "HIV stands for Human Immunodeficiency Virus.\n",
            [(0.8, "guide.pdf - page 1")]))

    def timeout(*args, **kwargs):
        raise chat_service.httpx.ReadTimeout("late response")

    monkeypatch.setattr(chat_service.ollama, "stream", timeout)

    result = chat_service._docs("What is HIV?", "en", [])

    assert result.text.startswith("The AI request timed out.")
    assert "Human Immunodeficiency Virus" in result.text
    assert "Sources :" not in result.text
    assert "[RAG section=" not in result.text
    assert result.sources == ()


def test_answer_rejects_greeting_only_completion(monkeypatch):
    monkeypatch.setattr(chat_service, "audit", lambda *args: None)
    monkeypatch.setattr(chat_service.router, "route",
                        lambda *args: chat_service.router.Route("chat", "question autonome"))
    monkeypatch.setattr(chat_service, "_general",
                        lambda *args: AnswerResult("Bonjour !", "CHAT"))

    result = chat_service.answer("Parle-moi de cette organisation")

    assert result.mode == "CHAT"
    assert result.text.startswith("Je n'ai pas pu formuler une réponse utile.")
