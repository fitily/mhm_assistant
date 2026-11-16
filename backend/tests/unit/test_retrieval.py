from types import SimpleNamespace

from app.domain.retrieval import documents
from app.services import chat_service


def test_below_threshold_returns_no_context(monkeypatch):
    settings = SimpleNamespace(top_k=4, min_score=0.55, max_context_chars=1000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    monkeypatch.setattr(documents.ollama, "embed", lambda texts, **kwargs: [[0.0]])
    monkeypatch.setattr(documents.vectors, "similar", lambda vector, k: [
        {"score": 0.54, "file_name": "guide.pdf", "page": 1, "content": "irrelevant"}])

    assert documents.get_doc_context("question") == ("", [])


def test_french_query_is_translated_before_vector_search(monkeypatch):
    settings = SimpleNamespace(top_k=4, min_score=0.55, max_context_chars=1000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    monkeypatch.setattr(documents.ollama, "complete", lambda *args, **kwargs: "What is HIV?")
    embedded = []
    monkeypatch.setattr(documents.ollama, "embed",
                        lambda texts, **kwargs: embedded.extend(texts) or [[0.0]])
    monkeypatch.setattr(documents.vectors, "similar", lambda vector, k: [
        {"score": 0.56, "file_name": "guide.pdf", "page": 1, "content": "HIV definition"}])

    context, sources = documents.get_doc_context("C'est quoi le VIH ?", language="fr")

    assert embedded == ["What is HIV?"]
    assert "HIV definition" in context
    assert sources == [(0.56, "guide.pdf - page 1")]


def test_malagasy_query_is_translated_before_vector_search(monkeypatch):
    seen = []
    monkeypatch.setattr(
        documents.ollama, "complete",
        lambda prompt, *args, **kwargs: seen.append(prompt) or "What are HIV symptoms?")

    translated = documents._english_query("Inona no soritr'aretin'ny VIH?", [], "mg")

    assert translated == "What are HIV symptoms?"
    assert "English search query" in seen[0]


def test_empty_retrieval_does_not_call_the_llm(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context", lambda *args: ("", []))

    def unexpected_call(*args, **kwargs):
        raise AssertionError("appel LLM inattendu")

    monkeypatch.setattr(chat_service.ollama, "complete", unexpected_call)

    result = chat_service._docs("question", "fr", [])

    assert result.text == "Je ne trouve pas cette information dans les documents disponibles."


def test_document_citations_are_built_from_retrieved_metadata(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : contenu", [(0.8, "guide.pdf - page 1")]))
    monkeypatch.setattr(chat_service.ollama, "stream",
                        lambda *args, **kwargs:
                        "A grounded answer.\nSources: autre.pdf - page 5")

    result = chat_service._docs("question", "fr", [])

    assert "autre.pdf" not in result.text
    assert "guide.pdf - page 1" in result.text


def test_context_keeps_three_relevant_excerpts_of_at_most_600_characters(monkeypatch):
    settings = SimpleNamespace(top_k=5, min_score=0.55, max_context_chars=7000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    monkeypatch.setattr(documents.ollama, "embed", lambda texts, **kwargs: [[0.0]])
    relevant = "Background. " * 40 + "HIV stands for Human Immunodeficiency Virus. " + "Unrelated. " * 60
    monkeypatch.setattr(documents.vectors, "similar", lambda vector, k: [
        {"score": 0.9 - index / 100, "file_name": f"guide{index}.pdf",
         "page": index + 1, "content": relevant}
        for index in range(4)])

    context, sources = documents.get_doc_context("HIV stand for")

    excerpts = context.split("\n---\n")
    excerpt_texts = [
        part.split("\n", 2)[2] if part.startswith("EXTRAITS :")
        else part.split("\n", 1)[1]
        for part in excerpts
    ]
    assert len(sources) == 3
    assert len(excerpts) == 3
    assert all(len(text.strip()) <= 600 for text in excerpt_texts)
    assert all("HIV stands for Human Immunodeficiency Virus" in part for part in excerpts)


def test_abstract_excerpt_focuses_on_results_instead_of_background():
    content = (
        "[RAG section=abstract type=prose]\n"
        + "Background about the topic. " * 40
        + "Results: Blood transmission awareness was 92.6%. "
        + "Knowledge was correlated with age and education.")

    excerpt = documents._relevant_excerpt(content, "HIV in Saudi Arabia")

    assert "Results:" in excerpt
    assert "Blood transmission awareness" in excerpt
    assert "Background about the topic" not in excerpt


def test_research_reranking_promotes_results_tables_and_conclusion():
    retrieved = [
        {"file_name": "study.pdf", "page": 1, "score": 0.91,
         "content": "[RAG section=introduction type=prose]\nBackground"},
        {"file_name": "study.pdf", "page": 1, "score": 0.60,
         "content": "[RAG section=abstract type=prose]\nStudy summary"},
        {"file_name": "study.pdf", "page": 2, "score": 0.74,
         "content": "[RAG section=results type=prose]\nKey results"},
        {"file_name": "study.pdf", "page": 3, "score": 0.73,
         "content": "[RAG section=results type=table table=2]\nTransmission"},
        {"file_name": "study.pdf", "page": 4, "score": 0.72,
         "content": "[RAG section=results type=table table=3]\nAttitudes"},
        {"file_name": "study.pdf", "page": 6, "score": 0.68,
         "content": "[RAG section=conclusion type=prose]\nConclusion"},
    ]

    ranked, is_research = documents._rank_hits(retrieved, 3)

    assert is_research
    assert [hit["content"].splitlines()[0] for hit in ranked] == [
        "[RAG section=results type=table table=2]",
        "[RAG section=results type=table table=3]",
        "[RAG section=conclusion type=prose]",
    ]


def test_legacy_research_chunks_are_tagged_in_the_retrieved_context(monkeypatch):
    settings = SimpleNamespace(top_k=4, min_score=0.55, max_context_chars=7000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    monkeypatch.setattr(documents.ollama, "embed", lambda texts, **kwargs: [[0.0]])
    monkeypatch.setattr(documents.vectors, "similar", lambda vector, k: [
        {"file_name": "study.pdf", "page": 1, "score": 0.9,
         "content": "1. INTRODUCTION Prior work was limited."},
        {"file_name": "study.pdf", "page": 3, "score": 0.7,
         "content": "Table 2. Awareness of transmission. Blood exposure 92%."},
        {"file_name": "study.pdf", "page": 6, "score": 0.65,
         "content": "CONCLUSION Awareness gaps remained."},
    ])

    context, _ = documents.get_doc_context("HIV awareness")

    assert "[RAG section=results type=table table=2]" in context
    assert "[RAG section=conclusion type=prose]" in context


def test_legacy_research_retrieval_excludes_background_references_and_other_studies():
    retrieved = [
        {"file_name": "study.pdf", "page": 1, "score": 0.91,
         "content": "1. INTRODUCTION Prior work was limited."},
        {"file_name": "study.pdf", "page": 7, "score": 0.85,
         "content": "References Author A. PMID: 12345. Author B. PMID: 67890."},
        {"file_name": "study.pdf", "page": 4, "score": 0.70,
         "content": "Table 3 illustrates the attitudes. Table 4 shows knowledge scores."},
        {"file_name": "study.pdf", "page": 3, "score": 0.74,
         "content": "Table 2. Awareness of transmission. Blood exposure 92%."},
        {"file_name": "study.pdf", "page": 6, "score": 0.67,
         "content": "5. CONCLUSION Awareness gaps remained."},
        {"file_name": "other-study.pdf", "page": 2, "score": 0.90,
         "content": "[RAG section=results type=prose]\nA separate study."},
    ]

    ranked, is_research = documents._rank_hits(retrieved, 3)

    assert is_research
    assert [hit["page"] for hit in ranked] == [3, 4, 6]
    assert all(hit["file_name"] == "study.pdf" for hit in ranked)
    assert [documents._section_info(hit)[0] for hit in ranked] == [
        "results", "results", "conclusion"]


def test_research_retrieval_recovers_attitude_table_below_global_threshold(monkeypatch):
    settings = SimpleNamespace(top_k=4, min_score=0.55, max_context_chars=7000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    monkeypatch.setattr(documents.ollama, "embed", lambda texts, **kwargs: [[0.0]])
    monkeypatch.setattr(documents.vectors, "similar", lambda vector, k: [
        {"file_name": "study.pdf", "page": 1, "score": 0.91,
         "content": "[RAG section=introduction type=prose]\nBackground"},
        {"file_name": "study.pdf", "page": 1, "score": 0.80,
         "content": "[RAG section=abstract type=prose]\nStudy summary"},
        {"file_name": "study.pdf", "page": 2, "score": 0.75,
         "content": "[RAG section=results type=table table=1]\n"
                    "Table 1. Demographic profile of respondents."},
        {"file_name": "study.pdf", "page": 3, "score": 0.70,
         "content": "[RAG section=results type=table table=2]\n"
                    "Table 2. Awareness of HIV transmission."},
        {"file_name": "study.pdf", "page": 4, "score": 0.48,
         "content": "[RAG section=results type=table table=3]\n"
                    "Table 3. Stigmatizing attitudes toward PLWHA."},
        {"file_name": "other.pdf", "page": 1, "score": 0.47,
         "content": "[RAG section=results type=prose]\nDifferent study."},
    ])

    context, sources = documents.get_doc_context("HIV in Saudi Arabia")

    assert "Table 2. Awareness" in context
    assert "Table 3. Stigmatizing attitudes" in context
    assert "Study summary" in context
    assert "Demographic profile" not in context
    assert "Background" not in context
    assert all("study.pdf" in source for _, source in sources)


def test_research_search_expands_to_retrieve_attitude_table(monkeypatch):
    settings = SimpleNamespace(top_k=4, min_score=0.55, max_context_chars=7000)
    monkeypatch.setattr(documents, "get_settings", lambda: settings)
    embeddings = []

    def embed(texts, **kwargs):
        embeddings.append(texts[0])
        return [[float(len(embeddings))]]

    monkeypatch.setattr(documents.ollama, "embed", embed)

    def similar(vector, k):
        if vector == [1.0]:
            return [
                {"file_name": "study.pdf", "page": 1, "score": 0.8,
                 "content": "[RAG section=abstract type=prose]\nStudy summary."},
                {"file_name": "study.pdf", "page": 3, "score": 0.7,
                 "content": "[RAG section=results type=table table=2]\n"
                            "Table 2. Transmission awareness."},
            ]
        return [
            {"file_name": "study.pdf", "page": 4, "score": 0.6,
             "content": "[RAG section=results type=table table=3]\n"
                        "Table 3. Stigmatizing attitudes."},
        ]

    monkeypatch.setattr(documents.vectors, "similar", similar)

    context, _ = documents.get_doc_context(
        "Do you have any clues about HIV in Saudi Arabia?")

    assert "Table 2. Transmission awareness" in context
    assert "Table 3. Stigmatizing attitudes" in context
    assert "public awareness stigmatizing attitudes results tables" in embeddings[1]


def test_useless_document_response_is_rejected(monkeypatch):
    monkeypatch.setattr(chat_service, "get_doc_context",
                        lambda *args: ("EXTRAITS : contexte", [(0.8, "guide.pdf - page 1")]))
    monkeypatch.setattr(chat_service.ollama, "stream",
                        lambda *args, **kwargs: "Hello, how can I help?")

    result = chat_service._docs("What is in this document?", "en", [])

    assert result.text.startswith("I cannot find this information in the available documents.")
    assert "guide.pdf - page 1" in result.text
