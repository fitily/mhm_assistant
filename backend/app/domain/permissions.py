"""Droits par rôle : quelle source de réponse chaque profil peut utiliser.

  doctor : documents (DOCS)        + conversation (CHAT)
  admin  : statistiques (SQL)      + conversation (CHAT) + tableaux de bord Superset (DASHBOARD)

Les routes /v1/superset/... sont réservées à « admin » par `require_role("admin")` (api/superset.py) ;
le mode DASHBOARD couvre les commandes du chat (« ouvre le tableau de bord ... »).
"""
from __future__ import annotations

from app.core.security import ROLE_ADMIN, ROLE_DOCTOR

ALLOWED_MODES: dict[str, frozenset[str]] = {
    ROLE_DOCTOR: frozenset({"DOCS", "CHAT"}),
    ROLE_ADMIN: frozenset({"SQL", "CHAT", "DASHBOARD"}),
}


def is_allowed(role: str | None, mode: str) -> bool:
    """True si ce rôle peut utiliser ce mode. Un rôle inconnu (ou absent) n'a droit à rien."""
    return mode in ALLOWED_MODES.get(role or "", frozenset())
