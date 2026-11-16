"""POST /v1/chat : pose une question à l'assistant."""
from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import current_user, sessions
from app.core.config import ASSISTANT_NAME, debug_trace
from app.domain import router as chat_router
from app.schemas.chat import ChatRequest, ChatResponse, ClearRequest, Source
from app.services import chat_service

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: str = Depends(current_user)) -> ChatResponse:
    # `def` (et non `async def`) : FastAPI l'exécute dans un thread, le LLM ne bloque pas le serveur.
    memory = sessions.get(f"{user}:{req.session_id or 'default'}")
    result = chat_service.answer(req.question, forced=req.mode, history=memory.history, user=user)
    memory.add(req.question, result.text)
    return ChatResponse(
        text=result.text, sender=ASSISTANT_NAME, mode=result.mode,
        sql=result.sql, notes=list(result.notes),
        sources=[Source(score=s, label=l) for s, l in result.sources], data=result.data)


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, user: str = Depends(current_user)) -> StreamingResponse:
    memory = sessions.get(f"{user}:{req.session_id or 'default'}")
    events: queue.Queue[tuple[str, dict] | None] = queue.Queue()

    def run() -> None:
        try:
            result = chat_service.answer(
                req.question, forced=req.mode, history=memory.history, user=user,
                on_docs_wait=lambda: events.put(
                    ("status", {"text": {
                        "en": f"{ASSISTANT_NAME}> Searching the documents…",
                        "fr": f"{ASSISTANT_NAME}> Recherche dans les documents…",
                        "mg": f"{ASSISTANT_NAME}> Mikaroka ao amin'ny antontan-taratasy…",
                    }[chat_router.detect_lang(req.question)]})),
                on_docs_token=lambda piece: events.put(("token", {"text": piece})))
            memory.add(req.question, result.text)
            response = ChatResponse(
                text=result.text, sender=ASSISTANT_NAME, mode=result.mode,
                sql=result.sql, notes=list(result.notes),
                sources=[Source(score=score, label=label) for score, label in result.sources],
                data=result.data)
            events.put(("complete", response.model_dump()))
        except Exception as exc:
            debug_trace("API flux échoué", error=type(exc).__name__)
            language = chat_router.detect_lang(req.question)
            message = {
                "fr": "La demande a échoué. Veuillez réessayer.",
                "mg": "Tsy nahomby ny fangatahana. Andramo indray azafady.",
                "en": "The request failed. Please try again.",
            }[language]
            events.put(("error", {"text": message}))
        finally:
            events.put(None)

    def stream_events() -> Iterator[str]:
        threading.Thread(target=run, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                break
            name, payload = event
            yield f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream_events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/clear")
def clear(req: ClearRequest, user: str = Depends(current_user)) -> dict[str, str]:
    memory = sessions.get(f"{user}:{req.session_id or 'default'}")
    memory.clear()
    return {"status": "cleared"}
