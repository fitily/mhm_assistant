"""Client Ollama minimal (HTTP) : génération, streaming et embeddings."""
from __future__ import annotations

import json
import time
from collections.abc import Callable

import httpx

from app.core.config import debug_trace, get_settings

OLLAMA_TIMEOUT = httpx.Timeout(connect=10, read=180, write=10, pool=10)


def estimate_tokens(text: str) -> int:
    """Approximation utilisée seulement quand Ollama ne renvoie pas sa mesure."""
    return (len(text) + 3) // 4


def _payload(prompt: str, predict: int, stream: bool, temperature: float = 0.0,
             response_format: str | None = None, num_ctx: int | None = None) -> dict:
    s = get_settings()
    payload = {
        "model": s.llm_model, "prompt": prompt, "stream": stream, "keep_alive": "30m",
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx if num_ctx is not None else s.num_ctx,
            "num_predict": predict,
        },
    }
    if response_format:
        payload["format"] = response_format
    return payload


def complete(prompt: str, predict: int = 300, temperature: float = 0.0,
             response_format: str | None = None, *, stage: str = "génération",
             num_ctx: int | None = None) -> str:
    started = time.perf_counter()
    try:
        r = httpx.post(
            f"{get_settings().ollama_host}/api/generate",
            json=_payload(prompt, predict, False, temperature, response_format, num_ctx),
            timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        result = data["response"].strip()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        debug_trace(
            "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
            prompt_tokens=estimate_tokens(prompt), result_tokens=None,
            token_count_source="estimated", error=type(exc).__name__,
            timeout={"connect_seconds": 10, "read_seconds": 180})
        raise
    debug_trace(
        "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
        prompt_tokens=data.get("prompt_eval_count", estimate_tokens(prompt)),
        result_tokens=data.get("eval_count", estimate_tokens(result)),
        token_count_source="ollama" if "prompt_eval_count" in data else "estimated",
        timeout={"connect_seconds": 10, "read_seconds": 180})
    return result


def stream(prompt: str, predict: int = 300, emit: Callable[[str], None] | None = None, *,
           stage: str = "génération", num_ctx: int | None = None) -> str:
    """Génère en flux ; `emit(morceau)` est appelé à chaque morceau (affichage en direct)."""
    chunks: list[str] = []
    url = f"{get_settings().ollama_host}/api/generate"
    started = time.perf_counter()
    metadata: dict = {}
    try:
        with httpx.stream(
                "POST", url, json=_payload(prompt, predict, True, num_ctx=num_ctx),
                timeout=OLLAMA_TIMEOUT) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                piece = data.get("response", "")
                chunks.append(piece)
                if "prompt_eval_count" in data or "eval_count" in data:
                    metadata = data
                if emit and piece:
                    emit(piece)
    except (httpx.HTTPError, ValueError) as exc:
        partial = "".join(chunks)
        debug_trace(
            "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
            prompt_tokens=metadata.get("prompt_eval_count", estimate_tokens(prompt)),
            result_tokens=metadata.get("eval_count", estimate_tokens(partial)),
            token_count_source="ollama" if "prompt_eval_count" in metadata else "estimated",
            error=type(exc).__name__, timeout={"connect_seconds": 10, "read_seconds": 180})
        raise
    result = "".join(chunks).strip()
    debug_trace(
        "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
        prompt_tokens=metadata.get("prompt_eval_count", estimate_tokens(prompt)),
        result_tokens=metadata.get("eval_count", estimate_tokens(result)),
        token_count_source="ollama" if "prompt_eval_count" in metadata else "estimated",
        timeout={"connect_seconds": 10, "read_seconds": 180})
    return result


def embed(texts: list[str], *, stage: str = "embedding") -> list[list[float]]:
    s = get_settings()
    prompt = "\n".join(texts)
    started = time.perf_counter()
    try:
        r = httpx.post(
            f"{s.ollama_host}/api/embed",
            json={"model": s.embed_model, "input": texts}, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        embeddings = data["embeddings"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        debug_trace(
            "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
            prompt_tokens=estimate_tokens(prompt), result_tokens=0,
            token_count_source="estimated", error=type(exc).__name__,
            timeout={"connect_seconds": 10, "read_seconds": 180})
        raise
    debug_trace(
        "LLM étape", stage=stage, duration_ms=round((time.perf_counter() - started) * 1000, 2),
        prompt_tokens=data.get("prompt_eval_count", estimate_tokens(prompt)), result_tokens=0,
        token_count_source="ollama" if "prompt_eval_count" in data else "estimated",
        timeout={"connect_seconds": 10, "read_seconds": 180},
        output="embedding vectors; no text tokens")
    return embeddings


def is_up() -> bool:
    try:
        return httpx.get(f"{get_settings().ollama_host}/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False
