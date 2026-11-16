"""Authentification : Laravel connecte l'utilisateur et envoie un jeton JWT signé.

FastAPI vérifie seulement la signature (secret partagé JWT_SECRET). Les rôles et les
mots de passe restent gérés par Laravel : on ne les recrée pas ici.
"""
from __future__ import annotations

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


def authenticate(token: str | None) -> str:
    """Retourne l'identifiant de l'utilisateur (claim « sub ») ou lève une erreur 401."""
    s = get_settings()
    if s.auth_disabled:
        return "dev-local"
    if not s.jwt_secret:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "JWT_SECRET non configuré.")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton manquant.")
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré.") from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton sans identifiant utilisateur.")
    return str(subject)
