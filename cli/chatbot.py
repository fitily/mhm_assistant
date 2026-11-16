"""Chatbot en ligne de commande (outil opérateur local de confiance).

    python cli/chatbot.py            # conversation
    python cli/chatbot.py ingest data/documents [--reset]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.domain.conversation import ConversationMemory  # noqa: E402
from app.domain.router import detect_lang  # noqa: E402
from app.core.config import ASSISTANT_NAME  # noqa: E402
from app.core.config import debug_trace  # noqa: E402
from app.infrastructure.db.analytics import source_views  # noqa: E402
from app.services.chat_service import answer  # noqa: E402

HELP = {
    "en": "/sql and /docs force a source; /views lists available views; /audit shows the last SQL; "
         "/clear clears the conversation. Enter a blank line to quit.",
    "fr": "/sql et /docs forcent la source ; /views liste les vues visibles ; /audit affiche le "
          "dernier SQL ; /clear efface la conversation. Ligne vide = quitter.",
    "mg": "/sql sy /docs no manery ny loharano; /views mampiseho ny lisitry ny views; "
          "/audit mampiseho ny SQL farany; /clear mamafa ny resaka. Tsipika banga = mivoaka.",
}


def format_reply(text: str) -> str:
    return f"{ASSISTANT_NAME}> {text}"


def show_views(language: str) -> str:
    try:
        separator = {"en": ": ", "fr": " : ", "mg": ": "}[language]
        empty = {
            "en": "(no visible views)",
            "fr": "(aucune vue visible)",
            "mg": "(tsy misy view hita)",
        }[language]
        return "\n".join(
            f"{schema}{separator}{', '.join(names) or empty}"
            for schema, names in source_views().items())
    except Exception as exc:  # noqa: BLE001
        debug_trace("CLI vues indisponibles", error=type(exc).__name__)
        return {
            "en": "Unable to read views.",
            "fr": "Impossible de lire les vues.",
            "mg": "Tsy azo vakina ny lisitry ny views.",
        }[language]


def chat() -> None:
    print(format_reply(
        f"Hello, I'm {ASSISTANT_NAME}, the AI assistant at MHM Ambovo. Ask me a question."))
    memory, last, language = ConversationMemory(), None, "en"
    while True:
        try:
            question = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        low = question.lower()
        if not low.startswith("/"):
            language = detect_lang(question)
        if low == "/clear":
            memory.clear()
            print(format_reply({
                "en": "Conversation cleared.",
                "fr": "Conversation effacée.",
                "mg": "Voafafa ny resaka.",
            }[language]))
        elif low == "/help":
            print(format_reply(HELP[language]))
        elif low == "/views":
            print(format_reply(show_views(language)))
        elif low == "/audit":
            print(format_reply({
                "en": "No request." if last is None else
                      f"Mode: {last.mode}\nSQL: {last.sql or '(none)'}\n{last.raw_result or ''}",
                "fr": "Aucune requête." if last is None else
                      f"Mode : {last.mode}\nSQL : {last.sql or '(aucun)'}\n{last.raw_result or ''}",
                "mg": "Tsy nisy fangatahana." if last is None else
                      f"Fomba: {last.mode}\nSQL: {last.sql or '(tsy misy)'}\n{last.raw_result or ''}",
            }[language]))
        else:
            m = re.match(r"^/(sql|docs)\s+(.*)$", question, re.I | re.S)
            forced, q = (m.group(1).upper(), m.group(2)) if m else (None, question)
            try:
                last = answer(q, forced=forced, history=memory.history, user="cli")
                print(format_reply(f"{last.text}\n[Mode : {last.mode}]"))
                memory.add(q, last.text)
            except Exception as exc:  # noqa: BLE001
                debug_trace("CLI demande échouée", error=type(exc).__name__)
                print(format_reply({
                    "en": "The request failed. Please try again.",
                    "fr": "La demande a échoué. Veuillez réessayer.",
                    "mg": "Tsy nahomby ny fangatahana. Andramo indray azafady.",
                }[language]))


if __name__ == "__main__":
    if sys.argv[1:2] == ["ingest"] and len(sys.argv) >= 3:
        from app.domain.retrieval.ingest import ingest_folder
        n = ingest_folder(Path(sys.argv[2]), reset="--reset" in sys.argv)
        print(f"{n} passages ajoutés.")
    else:
        chat()
