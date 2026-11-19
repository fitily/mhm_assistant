"""Dépendances FastAPI : utilisateur courant (jeton Laravel) et sessions de conversation."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import Principal, authenticate, decode_token
from app.domain.conversation import SessionStore

_bearer = HTTPBearer(auto_error=False)
sessions = SessionStore()


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    return authenticate(creds.credentials if creds else None)


def current_principal(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal:
    """Utilisateur connecté avec son rôle (« doctor » ou « admin »)."""
    return decode_token(creds.credentials if creds else None)


def require_role(*roles: str):
    """Réserve une route à certains rôles : `Depends(require_role("admin"))`. Sinon erreur 403."""
    allowed = frozenset(roles)

    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé pour votre profil.")
        return principal

    return dependency
