"""Droits par rôle : quelle source de réponse chaque profil peut utiliser.

  doctor : documents (DOCS)        + conversation (CHAT)
  admin  : statistiques (SQL)      + conversation (CHAT)

Les dashboards Superset seront réservés à « admin » avec `require_role("admin")` (voir api/deps.py).
"""
from __future__ import annotations

from app.core.security import ROLE_ADMIN, ROLE_DOCTOR

ALLOWED_MODES: dict[str, frozenset[str]] = {
    ROLE_DOCTOR: frozenset({"DOCS", "CHAT"}),
    ROLE_ADMIN: frozenset({"SQL", "CHAT"}),
}


def is_allowed(role: str | None, mode: str) -> bool:
    """True si ce rôle peut utiliser ce mode. Un rôle inconnu (ou absent) n'a droit à rien."""
    return mode in ALLOWED_MODES.get(role or "", frozenset())
