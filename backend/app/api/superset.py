"""GET /v1/superset/dashboards : catalogue ; POST /v1/superset/guest-token : accès temporaire à un dashboard.

Réservé au rôle « admin » (le médecin reçoit 403, une personne non connectée 401).
Le navigateur ne choisit qu'une CLÉ du catalogue : l'UUID est toujours retrouvé côté serveur.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_role
from app.core.audit import audit
from app.core.config import get_settings
from app.core.errors import (
    ConfigurationError,
    SupersetAuthError,
    SupersetError,
    SupersetRejected,
    SupersetUnavailable,
)
from app.core.security import ROLE_ADMIN, Principal
from app.schemas.superset import DashboardOut, GuestTokenRequest, GuestTokenResponse
from app.services import superset_service
from app.services.superset_service import UnknownDashboard

log = logging.getLogger("mhm.superset")
router = APIRouter(prefix="/v1/superset", tags=["superset"])

admin_only = require_role(ROLE_ADMIN)


@router.get("/dashboards", response_model=list[DashboardOut])
def dashboards(_: Principal = Depends(admin_only)) -> list[DashboardOut]:
    try:
        items = superset_service.list_dashboards()
    except ConfigurationError as exc:
        log.error("Catalogue de dashboards invalide : %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Dashboards indisponibles.") from None
    return [DashboardOut(key=d.key, title=d.title, description=d.description) for d in items]


@router.post("/guest-token", response_model=GuestTokenResponse)
def guest_token(req: GuestTokenRequest, response: Response,
                principal: Principal = Depends(admin_only)) -> GuestTokenResponse:
    # `def` (et non `async def`) : l'appel à Superset est bloquant, FastAPI l'exécute dans un thread.
    response.headers["Cache-Control"] = "no-store"  # un jeton ne doit jamais être mis en cache
    try:
        access = superset_service.create_guest_access(req.dashboard, principal)
    except UnknownDashboard:
        audit(principal.user, f"(dashboard:{req.dashboard[:40]})", "SUPERSET", "unknown_dashboard", None, None)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard inconnu.") from None
    except SupersetUnavailable as exc:
        log.warning("Superset indisponible : %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Superset est momentanément indisponible. Réessayez plus tard.") from None
    except (SupersetAuthError, SupersetRejected, ConfigurationError, SupersetError) as exc:
        # Problème de configuration côté serveur : détail dans les journaux, message neutre pour l'utilisateur.
        log.error("Échec du jeton invité (%s) : %s", type(exc).__name__, exc)
        audit(principal.user, f"(dashboard:{req.dashboard})", "SUPERSET", "guest_token_failed", None, None)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            "Impossible d'afficher ce dashboard pour le moment.") from None

    audit(principal.user, f"(dashboard:{access.dashboard.key})", "SUPERSET", "guest_token_ok", None, None)
    return GuestTokenResponse(
        dashboard_key=access.dashboard.key,
        dashboard_id=access.dashboard.uuid,
        token=access.token,
        expires_at=access.expires_at,
        superset_domain=get_settings().superset_public_url,
    )
