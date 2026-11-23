"""Accès aux dashboards Superset : catalogue + jeton invité limité à un seul dashboard.

Ce service ne vérifie PAS le rôle de l'utilisateur : c'est le travail de la route
(`require_role("admin")`, étape suivante). Il vérifie en revanche que la clé existe dans le catalogue.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt

from app.core.config import get_settings
from app.core.security import Principal
from app.domain.dashboard_catalog import Dashboard, UnknownDashboard, get_catalog
from app.infrastructure.superset.client import SupersetClient

__all__ = ["GuestAccess", "UnknownDashboard", "create_guest_access", "list_dashboards"]


@dataclass(frozen=True)
class GuestAccess:
    dashboard: Dashboard
    token: str
    expires_at: int | None  # horodatage Unix lu dans le jeton (pour que le navigateur le renouvelle)


@lru_cache(maxsize=1)
def get_client() -> SupersetClient:
    s = get_settings()
    return SupersetClient(s.superset_url, s.superset_username, s.superset_password, timeout=s.superset_timeout)


def list_dashboards() -> list[Dashboard]:
    return get_catalog().all()


def _expiry(token: str) -> int | None:
    """Lit la date d'expiration du jeton SANS vérifier sa signature (information d'affichage seulement)."""
    try:
        exp = jwt.decode(token, options={"verify_signature": False}).get("exp")
        return int(exp) if exp is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def create_guest_access(key: str, principal: Principal, *, client: SupersetClient | None = None) -> GuestAccess:
    """Jeton invité pour le dashboard `key`. Lève UnknownDashboard si la clé n'est pas au catalogue."""
    dashboard = get_catalog().get(key)
    token = (client or get_client()).guest_token(
        dashboard.uuid, username=principal.user, first_name=principal.name or "", last_name="",
    )
    return GuestAccess(dashboard=dashboard, token=token, expires_at=_expiry(token))
