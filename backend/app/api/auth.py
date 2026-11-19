"""POST /v1/auth/login : connexion ; GET /v1/auth/me : qui suis-je ?"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import current_principal
from app.core.errors import ConfigurationError
from app.core.security import Principal
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services import auth_service

log = logging.getLogger("mhm.auth")
router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    # `def` (et non `async def`) : le calcul argon2 est lent volontairement, FastAPI l'exécute
    # dans un thread pour ne pas bloquer les autres requêtes.
    try:
        result = auth_service.login(req.username, req.password)
    except auth_service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Identifiant ou mot de passe incorrect.") from None
    except auth_service.TooManyAttempts as exc:
        minutes = max(1, -(-exc.retry_after // 60))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Trop de tentatives. Réessayez dans {minutes} minute(s).",
            headers={"Retry-After": str(exc.retry_after)}) from None
    except (ConfigurationError, SQLAlchemyError) as exc:
        log.error("Base des utilisateurs indisponible : %s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Service de connexion indisponible. Réessayez plus tard.") from None
    return LoginResponse(
        access_token=result.token, expires_in=result.expires_in,
        user=UserOut(email=result.email, name=result.name, role=result.role))


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(current_principal)) -> UserOut:
    return UserOut(email=principal.user, name=principal.name, role=principal.role)
