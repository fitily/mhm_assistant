"""Client Gemini (API REST de Google) : génération et streaming, TEMPORAIRE — pour comparer avec Llama 3.2.

Principe : `ollama.complete()` et `ollama.stream()` délèguent ici quand `is_enabled()` est vrai. Aucun appelant ne change.
Les embeddings (BGE-M3) et la santé restent sur Ollama : ce module ne s'en occupe pas.

Activation (tout se règle dans .env) :
    LLM_MODEL=gemini-…            -> Gemini est utilisé dès que le nom du modèle commence par « gemini »
    (ou) LLM_PROVIDER=gemini + GEMINI_MODEL=gemini-…
Clé API, par ordre de recherche : GEMINI_API_KEY, GOOGLE_API_KEY, puis OLLAMA_HOST si cette valeur n'est pas une URL
(usage temporaire connu : la clé a été placée dans OLLAMA_HOST).
Retour à Ollama : remettre LLM_MODEL=llama3.2 et OLLAMA_HOST=http://localhost:11434 — rien d'autre.

Sécurité : la clé voyage dans l'en-tête `x-goog-api-key`, jamais dans l'URL ; elle n'apparaît dans aucun journal ni message.
Fiabilité : nouvelles tentatives (429, 500, 502, 503, 504, coupures réseau) avec attente croissante ; les erreurs restent
des exceptions httpx, donc gérées par le code existant (délai dépassé, service indisponible…).
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from collections.abc import Callable

import httpx

from app.core.config import debug_trace

log = logging.getLogger("mhm.gemini")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT = httpx.Timeout(connect=10, read=120, write=10, pool=10)
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_WAIT = 20.0        # secondes : on n'attend jamais plus longtemps entre deux essais
THINKING_HEADROOM = 1024     # marge ajoutée à maxOutputTokens : la « réflexion » de certains modèles consomme ce quota
_transport: httpx.BaseTransport | None = None   # tests : httpx.MockTransport


class GeminiError(httpx.HTTPError):
    """Réponse Gemini inutilisable (bloquée, vide, tronquée) ou configuration incomplète."""


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def model_name() -> str:
    """Nom du modèle Gemini à utiliser, ou chaîne vide si Gemini n'est pas activé."""
    model = os.getenv("LLM_MODEL", "llama3.2").strip()
    if model.casefold().startswith(("gemini", "models/gemini")):
        return model.removeprefix("models/")
    if os.getenv("LLM_PROVIDER", "").strip().casefold() == "gemini":
        return os.getenv("GEMINI_MODEL", "").strip().removeprefix("models/")
    return ""


def is_enabled() -> bool:
    return bool(model_name()) or os.getenv("LLM_PROVIDER", "").strip().casefold() == "gemini"


def _api_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.getenv(name, "").strip():
            return os.environ[name].strip()
    legacy = os.getenv("OLLAMA_HOST", "").strip()
    if legacy and not _is_url(legacy):
        return legacy
    raise GeminiError("Clé API Gemini introuvable (GEMINI_API_KEY, ou OLLAMA_HOST s'il contient la clé).")


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def _body(prompt: str, predict: int, temperature: float, response_format: str | None) -> dict:
    config: dict = {"temperature": temperature, "maxOutputTokens": max(predict, 64) + THINKING_HEADROOM}
    if response_format == "json":
        config["responseMimeType"] = "application/json"
    thinking: dict = {}
    if os.getenv("GEMINI_THINKING_LEVEL", "").strip():       # modèles 3.x : minimal | low | medium | high
        thinking["thinkingLevel"] = os.environ["GEMINI_THINKING_LEVEL"].strip()
    if os.getenv("GEMINI_THINKING_BUDGET", "").strip():      # modèles 2.5 : nombre de jetons (0 = sans réflexion)
        thinking["thinkingBudget"] = int(os.environ["GEMINI_THINKING_BUDGET"])
    if thinking:
        config["thinkingConfig"] = thinking
    return {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}


def _url(action: str) -> str:
    model = model_name()
    if not model:
        raise GeminiError("Modèle Gemini non défini (LLM_MODEL=gemini-… ou GEMINI_MODEL=gemini-…).")
    return f"{BASE_URL}/models/{model}:{action}"


def _wait_seconds(attempt: int, response: httpx.Response | None) -> float:
    retry_after = response.headers.get("retry-after") if response is not None else None
    try:
        if retry_after:
            return min(float(retry_after), MAX_RETRY_WAIT)
    except ValueError:
        pass
    return min(2.0 ** attempt + random.uniform(0, 0.5), MAX_RETRY_WAIT)


def _max_retries() -> int:
    try:
        return max(0, int(os.getenv("GEMINI_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _send(url: str, body: dict, *, stream: bool) -> httpx.Response:
    """POST avec nouvelles tentatives. Pour le flux, la réponse est renvoyée ouverte (à fermer par l'appelant)."""
    headers = {"x-goog-api-key": _api_key(), "content-type": "application/json"}
    retries = _max_retries()
    for attempt in range(retries + 1):
        client = httpx.Client(timeout=TIMEOUT, transport=_transport)
        response: httpx.Response | None = None
        try:
            request = client.build_request("POST", url, json=body, headers=headers)
            response = client.send(request, stream=stream)
            if response.status_code not in RETRY_STATUS or attempt == retries:
                response.raise_for_status() if response.status_code >= 400 else None
                return response
            reason = f"HTTP {response.status_code}"
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            if attempt == retries:
                client.close()
                raise
            reason = type(exc).__name__
        except httpx.HTTPStatusError:
            if response is not None:
                response.close()
            client.close()
            raise
        wait = _wait_seconds(attempt, response)
        if response is not None:
            response.close()
        client.close()
        log.warning("Gemini : %s, nouvel essai %d/%d dans %.1f s", reason, attempt + 1, retries, wait)
        time.sleep(wait)
    raise GeminiError("Gemini indisponible.")  # pragma: no cover — la boucle renvoie ou lève toujours


def _text_of(data: dict) -> tuple[str, str | None]:
    """(texte, motif d'arrêt) d'une réponse ; lève GeminiError si la demande ou la réponse est bloquée."""
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise GeminiError(f"Demande bloquée par Gemini ({block}).")
    candidates = data.get("candidates") or []
    if not candidates:
        return "", None
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return text, candidate.get("finishReason")


def _check(text: str, finish: str | None) -> str:
    text = text.strip()
    if not text:
        raise GeminiError(f"Réponse Gemini vide (motif : {finish or 'inconnu'}).")
    return text


def complete(prompt: str, predict: int = 300, temperature: float = 0.0, response_format: str | None = None, *,
             stage: str = "génération", num_ctx: int | None = None) -> str:  # num_ctx : concept propre à Ollama
    started = time.perf_counter()
    data: dict = {}
    try:
        response = _send(_url("generateContent"), _body(prompt, predict, temperature, response_format), stream=False)
        data = response.json()
        text, finish = _text_of(data)
        result = _check(text, finish)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        debug_trace("LLM étape", stage=stage, provider="gemini", error=type(exc).__name__,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    prompt_tokens=estimate_tokens(prompt), result_tokens=None, token_count_source="estimated")
        raise
    usage = data.get("usageMetadata") or {}
    debug_trace("LLM étape", stage=stage, provider="gemini", model=model_name(),
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                prompt_tokens=usage.get("promptTokenCount", estimate_tokens(prompt)),
                result_tokens=usage.get("candidatesTokenCount", estimate_tokens(result)),
                token_count_source="gemini" if usage else "estimated")
    return result


def stream(prompt: str, predict: int = 300, emit: Callable[[str], None] | None = None, *,
           stage: str = "génération", num_ctx: int | None = None) -> str:
    """Génère en flux (SSE) ; `emit(morceau)` est appelé à chaque morceau. Réessaie seulement avant le premier morceau."""
    started = time.perf_counter()
    chunks: list[str] = []
    finish: str | None = None
    usage: dict = {}
    try:
        response = _send(_url("streamGenerateContent") + "?alt=sse", _body(prompt, predict, 0.0, None), stream=True)
        try:
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                data = json.loads(payload)
                piece, reason = _text_of(data)
                finish = reason or finish
                usage = data.get("usageMetadata") or usage
                chunks.append(piece)
                if emit and piece:
                    emit(piece)
        finally:
            response.close()
        result = _check("".join(chunks), finish)
    except (httpx.HTTPError, ValueError) as exc:
        debug_trace("LLM étape", stage=stage, provider="gemini", error=type(exc).__name__,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    prompt_tokens=estimate_tokens(prompt), result_tokens=estimate_tokens("".join(chunks)),
                    token_count_source="estimated")
        raise
    debug_trace("LLM étape", stage=stage, provider="gemini", model=model_name(),
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                prompt_tokens=usage.get("promptTokenCount", estimate_tokens(prompt)),
                result_tokens=usage.get("candidatesTokenCount", estimate_tokens(result)),
                token_count_source="gemini" if usage else "estimated")
    return result
