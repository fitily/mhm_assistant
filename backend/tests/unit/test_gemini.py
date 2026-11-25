"""Gemini (test temporaire) : activation, requêtes, erreurs, nouvelles tentatives, clé jamais exposée."""
import json

import httpx
import pytest

from app.core.config import get_settings
from app.infrastructure.llm import gemini, ollama

KEY = "AIza-FAKE-KEY-0123456789"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for name in ("LLM_MODEL", "LLM_PROVIDER", "GEMINI_MODEL", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                 "GEMINI_THINKING_LEVEL", "GEMINI_THINKING_BUDGET", "OLLAMA_HOST"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    monkeypatch.setattr(gemini, "_transport", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def use(monkeypatch, handler, model="gemini-test-flash", key_in="GEMINI_API_KEY"):
    monkeypatch.setenv("LLM_MODEL", model)
    monkeypatch.setenv(key_in, KEY)
    monkeypatch.setattr(gemini, "_transport", httpx.MockTransport(handler))
    get_settings.cache_clear()


def reply(text="Bonjour", **extra):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3}, **extra}


# --- activation et retour à Ollama ------------------------------------------------------------------------------

def test_disabled_by_default_and_ollama_untouched(monkeypatch):
    assert not gemini.is_enabled()
    called = {}
    monkeypatch.setattr(ollama.httpx, "post", lambda url, **kw: called.setdefault("url", url) and httpx.Response(
        200, json={"response": " ok "}, request=httpx.Request("POST", url)))
    assert ollama.complete("hi") == "ok" and called["url"].endswith("/api/generate")


def test_model_name_activates_gemini(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gemini-test-flash")
    assert gemini.is_enabled() and gemini.model_name() == "gemini-test-flash"
    monkeypatch.setenv("LLM_MODEL", "llama3.2")
    assert not gemini.is_enabled()


def test_provider_variable_with_separate_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "models/gemini-x")
    assert gemini.is_enabled() and gemini.model_name() == "gemini-x"


def test_api_key_in_ollama_host_is_used_and_ollama_keeps_its_default_url(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", KEY)
    get_settings.cache_clear()
    assert get_settings().ollama_host == "http://localhost:11434"  # embeddings BGE-M3 : adresse locale par défaut
    assert gemini._api_key() == KEY
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434/")
    get_settings.cache_clear()
    assert get_settings().ollama_host == "http://127.0.0.1:11434"


def test_missing_key_is_a_clear_error_without_network(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gemini-test-flash")
    with pytest.raises(gemini.GeminiError, match="Clé API"):
        ollama.complete("hi")


# --- requête / réponse ------------------------------------------------------------------------------------------

def test_complete_request_shape_and_key_header(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), key=request.headers.get("x-goog-api-key"), body=json.loads(request.content))
        return httpx.Response(200, json=reply("  Réponse  "))

    use(monkeypatch, handler)
    assert ollama.complete("Question ?", 300, 0.3, "json") == "Réponse"
    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test-flash:generateContent"
    assert KEY not in seen["url"] and seen["key"] == KEY
    cfg = seen["body"]["generationConfig"]
    assert cfg["temperature"] == 0.3 and cfg["responseMimeType"] == "application/json"
    assert cfg["maxOutputTokens"] >= 300 and "thinkingConfig" not in cfg
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "Question ?"


def test_optional_thinking_settings(monkeypatch):
    seen = {}
    use(monkeypatch, lambda r: (seen.update(b=json.loads(r.content)), httpx.Response(200, json=reply()))[1])
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "minimal")
    gemini.complete("x")
    assert seen["b"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "minimal"}
    monkeypatch.delenv("GEMINI_THINKING_LEVEL")
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "0")
    gemini.complete("x")
    assert seen["b"]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_thought_parts_are_not_returned(monkeypatch):
    data = {"candidates": [{"content": {"parts": [{"text": "réflexion", "thought": True}, {"text": "Vrai texte"}]}}]}
    use(monkeypatch, lambda r: httpx.Response(200, json=data))
    assert gemini.complete("x") == "Vrai texte"


def test_stream_collects_and_emits_chunks(monkeypatch):
    sse = "".join(f"data: {json.dumps(reply(t))}\n\n" for t in ("Bon", "jour"))
    use(monkeypatch, lambda r: httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"}))
    got = []
    assert ollama.stream("hi", emit=got.append) == "Bonjour" and got == ["Bon", "jour"]


# --- erreurs et fiabilité ---------------------------------------------------------------------------------------

def test_blocked_prompt_and_empty_answer_raise_http_errors(monkeypatch):
    use(monkeypatch, lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(httpx.HTTPError, match="bloquée"):
        gemini.complete("x")
    use(monkeypatch, lambda r: httpx.Response(200, json={"candidates": [{"finishReason": "MAX_TOKENS"}]}))
    with pytest.raises(httpx.HTTPError, match="MAX_TOKENS"):
        gemini.complete("x")


def test_rate_limit_is_retried_then_succeeds(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, json={"error": {"status": "RESOURCE_EXHAUSTED"}}, headers={"retry-after": "1"}) \
            if len(calls) < 3 else httpx.Response(200, json=reply("ok"))

    use(monkeypatch, handler)
    assert gemini.complete("x") == "ok" and len(calls) == 3


def test_persistent_overload_gives_an_httpx_error_after_the_limit(monkeypatch):
    calls = []
    use(monkeypatch, lambda r: (calls.append(1), httpx.Response(503, json={}))[1])
    with pytest.raises(httpx.HTTPStatusError):
        gemini.complete("x")
    assert len(calls) == 3  # 1 essai + 2 nouvelles tentatives
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "0")
    calls.clear()
    with pytest.raises(httpx.HTTPStatusError):
        gemini.complete("x")
    assert len(calls) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_are_not_retried_and_do_not_leak_the_key(monkeypatch, status):
    calls = []
    use(monkeypatch, lambda r: (calls.append(1), httpx.Response(status, json={"error": {"message": "x"}}))[1])
    with pytest.raises(httpx.HTTPStatusError) as err:
        gemini.complete("x")
    assert len(calls) == 1 and KEY not in str(err.value) and KEY not in repr(err.value)


def test_timeout_is_retried_and_stays_a_timeout_error(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("trop long", request=request)

    use(monkeypatch, handler)
    with pytest.raises(httpx.TimeoutException):  # les appelants existants gèrent déjà ce type
        gemini.complete("x")


def test_key_never_appears_in_logs(monkeypatch, caplog):
    use(monkeypatch, lambda r: httpx.Response(503, json={}))
    with caplog.at_level("DEBUG"), pytest.raises(httpx.HTTPError):
        gemini.complete("x")
    assert KEY not in caplog.text and "nouvel essai" in caplog.text
