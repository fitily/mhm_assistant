"""Dépendances FastAPI : utilisateur courant (jeton Laravel) et sessions de conversation."""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import authenticate
from app.domain.conversation import SessionStore

_bearer = HTTPBearer(auto_error=False)
sessions = SessionStore()


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    return authenticate(creds.credentials if creds else None)
