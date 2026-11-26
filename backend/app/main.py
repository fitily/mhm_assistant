"""Point d'entrée FastAPI :  uvicorn app.main:app --reload --port 8000"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, feeds, health, kpis, superset
from app.core.config import ASSISTANT_NAME, get_settings


def create_app() -> FastAPI:
    app = FastAPI(title=f"{ASSISTANT_NAME} — MHM Ambovo", version="0.1.0")
    origins = get_settings().cors_origins
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type"])
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(superset.router)
    app.include_router(kpis.router)
    app.include_router(feeds.router)
    return app


app = create_app()