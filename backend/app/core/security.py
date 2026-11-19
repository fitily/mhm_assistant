"""Authentification : FastAPI émet lui-même le jeton JWT à la connexion (POST /v1/auth/login).

Le jeton est signé avec le secret JWT_SECRET et contient l'identifiant de l'utilisateur (« sub »),
son rôle (« role ») et une date d'expiration (« exp »). Chaque requête suivante envoie ce jeton
dans l'en-tête « Authorization: Bearer ... » et FastAPI en vérifie la signature.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

ROLE_DOCTOR = "doctor"  # accès aux documents (RAG) uniquement
ROLE_ADMIN = "admin"    # accès aux statistiques (SQL) et aux dashboards Superset uniquement
ROLES = frozenset({ROLE_DOCTOR, ROLE_ADMIN})
MIN_SECRET_LENGTH = 32


@dataclass(frozen=True)
class Principal:
    """L'utilisateur connecté, tel que lu dans son jeton."""
    user: str
    role: str | None
    name: str | None = None


def decode_token(token: str | None) -> Principal:
    """Vérifie le jeton et retourne l'utilisateur et son rôle, ou lève une erreur 401."""
    s = get_settings()
    if s.auth_disabled:
        return Principal("dev-local", s.dev_role, "Développeur local")
    if not s.jwt_secret:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "JWT_SECRET non configuré.")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton manquant.")
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                             options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré.") from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton sans identifiant utilisateur.")
    role = payload.get("role")
    return Principal(str(subject), role if role in ROLES else None, payload.get("name"))


def authenticate(token: str | None) -> str:
    """Retourne l'identifiant de l'utilisateur (claim « sub ») ou lève une erreur 401."""
    return decode_token(token).user


def create_access_token(*, subject: str, role: str, name: str) -> tuple[str, int]:
    """Fabrique un jeton signé. Retourne (jeton, durée de validité en secondes)."""
    s = get_settings()
    if len(s.jwt_secret) < MIN_SECRET_LENGTH:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"JWT_SECRET doit contenir au moins {MIN_SECRET_LENGTH} caractères.")
    now = dt.datetime.now(dt.timezone.utc)
    lifetime = dt.timedelta(minutes=s.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "name": name, "iat": now, "exp": now + lifetime}
    token = jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, int(lifetime.total_seconds())
