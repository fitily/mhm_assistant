"""Accès aux dashboards Superset : catalogue + jeton invité limité à un seul dashboard.

Ce service ne vérifie PAS le rôle de l'utilisateur : c'est le travail de la route
(`require_role("admin")`, étape suivante). Il vérifie en revanche que la clé existe dans le catalogue.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, replace
from functools import lru_cache

import jwt

from app.core.config import get_settings
from app.core.errors import ConfigurationError, SupersetError
from app.core.security import Principal
from app.domain.dashboard_catalog import Dashboard, UnknownDashboard, get_catalog
from app.infrastructure.superset.client import SupersetClient

__all__ = ["GuestAccess", "UnknownDashboard", "clear_title_cache", "create_guest_access", "list_dashboards", "with_live_titles"]

log = logging.getLogger("mhm.superset")

TITLES_TTL = 60.0         # un renommage fait dans Superset apparaît ici au bout d'une minute au plus
TITLES_RETRY_AFTER = 60.0  # si Superset est en panne, on ne réessaie pas à chaque message du chat


@dataclass(frozen=True)
class GuestAccess:
    dashboard: Dashboard
    token: str
    expires_at: int | None  # horodatage Unix lu dans le jeton (pour que le navigateur le renouvelle)


@lru_cache(maxsize=1)
def get_client() -> SupersetClient:
    s = get_settings()
    return SupersetClient(s.superset_url, s.superset_username, s.superset_password, timeout=s.superset_timeout)


_titles_lock = threading.Lock()
_titles: dict[str, str] = {}   # {uuid: titre lu dans Superset} (dernier résultat connu)
_titles_at: float | None = None
_titles_ok = False


def clear_title_cache() -> None:
    global _titles, _titles_at, _titles_ok
    with _titles_lock:
        _titles, _titles_at, _titles_ok = {}, None, False


def _live_titles(dashboards: list[Dashboard], client: SupersetClient | None) -> dict[str, str]:
    """Titres actuels dans Superset, mis en cache. En cas d'échec, on garde les derniers titres connus."""
    global _titles, _titles_at, _titles_ok
    with _titles_lock:
        now = time.monotonic()
        if _titles_at is not None and now - _titles_at < (TITLES_TTL if _titles_ok else TITLES_RETRY_AFTER):
            return _titles
        try:
            _titles = (client or get_client()).dashboard_titles([d.uuid for d in dashboards])
            _titles_ok = True
        except (SupersetError, ConfigurationError) as exc:
            _titles_ok = False  # on garde _titles : derniers noms connus (ou titres du catalogue)
            log.warning("Noms des dashboards non synchronisés avec Superset (%s) : %s", type(exc).__name__, exc)
        _titles_at = now
        return _titles


def list_dashboards(*, sync: bool = True, client: SupersetClient | None = None) -> list[Dashboard]:
    """Dashboards du catalogue, avec le NOM défini dans Superset (le titre du catalogue sert de repli).

    Le catalogue reste la seule source de vérité de ce qui est autorisé (clés, UUID, mots-clés) ;
    Superset ne fournit que le nom affiché. `sync=False` : aucun appel à Superset (titres du catalogue).
    """
    dashboards = get_catalog().all()
    return with_live_titles(dashboards, client=client) if sync else dashboards


def with_live_titles(dashboards: list[Dashboard], *, client: SupersetClient | None = None) -> list[Dashboard]:
    """Même liste, avec le nom actuel de chaque dashboard dans Superset (repli : titre du catalogue)."""
    if not dashboards:
        return dashboards
    live = _live_titles(dashboards, client)
    return [replace(d, title=live[d.uuid]) if d.uuid in live else d for d in dashboards]


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
