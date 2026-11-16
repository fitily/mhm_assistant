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
