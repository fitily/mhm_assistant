"""Contrôle rapide de Gemini (test temporaire) : configuration, appel simple, mode JSON, flux.

    python scripts/check_gemini.py

N'affiche JAMAIS la clé. Ne touche à aucune base de données.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.infrastructure.llm import gemini, ollama  # noqa: E402


def key_source() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.getenv(name, "").strip():
            return name
    host = os.getenv("OLLAMA_HOST", "").strip()
    return "OLLAMA_HOST (contient la clé)" if host and not host.startswith(("http://", "https://")) else "introuvable"


def step(label: str, fn) -> bool:
    started = time.perf_counter()
    try:
        out = fn()
        print(f"  OK   {label:28} {time.perf_counter() - started:5.1f} s   {out}")
        return True
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        hint = {400: "requête refusée (modèle ou paramètre invalide ?)", 401: "clé refusée", 403: "clé sans droit / région",
                404: "nom de modèle introuvable", 429: "quota ou limite de requêtes atteint"}.get(code, "service Gemini")
        print(f"  ECHEC {label:27} HTTP {code} : {hint}")
    except httpx.TimeoutException:
        print(f"  ECHEC {label:27} délai dépassé")
    except httpx.HTTPError as exc:
        print(f"  ECHEC {label:27} {type(exc).__name__} : {exc}")
    return False


def main() -> int:
    print("Fournisseur actif :", f"Gemini ({gemini.model_name() or 'modèle non défini'})" if gemini.is_enabled() else "Ollama")
    print("Clé API           :", key_source(), "(valeur non affichée)")
    print("Ollama (embeddings):", get_settings().ollama_host, "-> joignable" if ollama.is_up() else "-> NON joignable")
    if not gemini.is_enabled():
        print("\nGemini n'est pas activé : mettez LLM_MODEL=gemini-… dans .env.")
        return 1
    print()
    results = [
        step("réponse simple", lambda: repr(ollama.complete("Réponds uniquement par le mot : OK", 20))),
        step("mode JSON (SQL, routeur)", lambda: json.loads(ollama.complete(
            'Réponds par un objet JSON {"ok": true}', 30, response_format="json"))),
        step("flux (chat documents)", lambda: repr(ollama.stream("Compte de 1 à 3, séparés par des virgules.", 30))),
    ]
    print("\nRésultat :", "tout fonctionne" if all(results) else "au moins une étape a échoué")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
