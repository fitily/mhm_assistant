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
from app.core.config import ASSISTANT_NAME  # noqa: E402
from app.infrastructure.db.analytics import message, source_views  # noqa: E402
from app.services.chat_service import answer  # noqa: E402

HELP = ("/sql et /docs forcent la source ; /views liste les vues visibles ; /audit affiche le "
        "dernier SQL ; /clear efface la conversation. Ligne vide = quitter.")


def format_reply(text: str) -> str:
    return f"{ASSISTANT_NAME}> {text}"


def show_views() -> str:
    try:
        return "\n".join(
            f"{schema} : {', '.join(names) or '(aucune vue visible)'}"
            for schema, names in source_views().items())
    except Exception as exc:  # noqa: BLE001
        return f"Impossible de lire les vues : {message(exc)}"


def chat() -> None:
    print(format_reply(
        f"Bonjour, je suis {ASSISTANT_NAME}, l'assistant IA de MHM Ambovo. Posez votre question."))
    memory, last = ConversationMemory(), None
    while True:
        try:
            question = input("\nVous> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        low = question.lower()
        if low == "/clear":
            memory.clear()
            print(format_reply("Conversation effacée."))
        elif low == "/help":
            print(format_reply(HELP))
        elif low == "/views":
            print(format_reply(show_views()))
        elif low == "/audit":
            print(format_reply("Aucune requête." if last is None else
                               f"Mode : {last.mode}\nSQL : {last.sql or '(aucun)'}\n"
                               f"{last.raw_result or ''}"))
        else:
            m = re.match(r"^/(sql|docs)\s+(.*)$", question, re.I | re.S)
            forced, q = (m.group(1).upper(), m.group(2)) if m else (None, question)
            try:
                last = answer(q, forced=forced, history=memory.history, user="cli")
                print(format_reply(f"{last.text}\n[Mode : {last.mode}]"))
                memory.add(q, last.text)
            except Exception as exc:  # noqa: BLE001
                print(format_reply(f"Erreur : {exc}"))


if __name__ == "__main__":
    if sys.argv[1:2] == ["ingest"] and len(sys.argv) >= 3:
        from app.domain.retrieval.ingest import ingest_folder
        n = ingest_folder(Path(sys.argv[2]), reset="--reset" in sys.argv)
        print(f"{n} passages ajoutés.")
    else:
        chat()
