"""Exceptions métier partagées."""
from __future__ import annotations


class ConfigurationError(RuntimeError):
    """Vues, dictionnaire ou connexion absents / mal configurés."""


class OutOfRange(RuntimeError):
    """La période demandée est hors de la plage couverte par les données."""


class QueryError(RuntimeError):
    def __init__(self, message: str, *, stage: str, sql: str | None = None,
                 details: str | None = None):
        super().__init__(message)
        self.stage, self.sql, self.details = stage, sql, details


class SupersetError(RuntimeError):
    """Base des erreurs liées à Superset. Les messages ne contiennent jamais de secret."""


class SupersetUnavailable(SupersetError):
    """Superset ne répond pas (arrêté, réseau, délai dépassé, erreur serveur)."""


class SupersetAuthError(SupersetError):
    """Le compte technique du backend est refusé ou n'a pas les droits nécessaires."""


class SupersetRejected(SupersetError):
    """Superset refuse la demande (dashboard inconnu, intégration non activée...)."""
