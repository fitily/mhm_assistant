"""GET /v1/kpis : indicateurs clés de la page Analytics. Réservé au rôle « admin » (médecin : 403)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_role
from app.core.errors import ConfigurationError
from app.core.security import ROLE_ADMIN, Principal
from app.schemas.kpis import KpiOut
from app.services import kpi_service

log = logging.getLogger("mhm.kpi")
router = APIRouter(prefix="/v1", tags=["kpis"])


@router.get("/kpis", response_model=list[KpiOut])
def kpis(response: Response, _: Principal = Depends(require_role(ROLE_ADMIN))) -> list[KpiOut]:
    try:
        values = kpi_service.get_kpis()
    except ConfigurationError as exc:
        log.error("Configuration des indicateurs invalide : %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Indicateurs indisponibles.") from None
    response.headers["Cache-Control"] = "no-store"
    return [KpiOut(key=v.key, label=v.label, value=v.value, hint=v.hint,
                   delta_percent=v.delta_percent, error=v.error) for v in values]
