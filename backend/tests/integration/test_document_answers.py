import pytest

from app.core.config import get_settings
from app.domain import router
from app.infrastructure.llm import ollama
from app.services.chat_service import answer


@pytest.fixture(scope="module", autouse=True)
def local_document_services():
    if not get_settings().vec_url.password or not ollama.is_up():
        pytest.skip("Les services locaux Ollama et PostgreSQL vectoriel sont requis.")


@pytest.mark.parametrize("question", [
    "what does HIV stand for",
    "c'est quoi le VIH",
    "HIV in Saudi Arabia",
    "do you have any clue about HIV in Saudi Arabia",
])
def test_real_document_answers_include_sources(question):
    history = [("Bonjour", "Bonjour, comment puis-je vous aider.")]
    result = answer(question, forced="DOCS", history=history, user="integration")

    assert result.mode == "DOCS"
    assert router.has_useful_content(result.text)
    assert result.sources
    assert all("page" in label for _, label in result.sources)
    if question == "what does HIV stand for":
        answer_text = result.text.split("\n\nSources :", 1)[0].lower()
        assert any(term in answer_text
                   for term in ("stands for", "means", "human immunodeficiency"))
    if question == "do you have any clue about HIV in Saudi Arabia":
        answer_text = result.text.split("\n\nSources :", 1)[0]
        assert router.detect_lang(answer_text) == "en"
