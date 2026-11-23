"""Modèles Pydantic des routes Superset (entrée / sortie)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardOut(BaseModel):
    key: str
    title: str
    description: str = ""
    available: bool = True


class GuestTokenRequest(BaseModel):
    dashboard: str = Field(min_length=1, max_length=64)  # une CLÉ du catalogue, jamais un UUID ni une URL


class GuestTokenResponse(BaseModel):
    dashboard_key: str
    dashboard_id: str          # UUID d'intégration : demandé par le SDK Superset côté navigateur
    token: str                 # jeton invité : limité à ce dashboard, courte durée
    expires_at: int | None = None  # horodatage Unix : le navigateur renouvelle avant cette date
    superset_domain: str       # adresse de Superset vue par le navigateur
