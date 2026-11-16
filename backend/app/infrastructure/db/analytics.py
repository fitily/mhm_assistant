"""Accès LECTURE SEULE à la base statistique (vues analytics) : timeout, EXPLAIN, requêtes."""
from __future__ import annotations

import json
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.errors import ConfigurationError, QueryError


@lru_cache(maxsize=1)
def engine():
    s = get_settings()
    if not s.src_url.password:
        raise ConfigurationError("SRC_PASSWORD est requis pour accéder à la base statistique.")
    return create_engine(
        s.src_url, pool_pre_ping=True,
        connect_args={"options": (
            "-c default_transaction_read_only=on "
            f"-c statement_timeout={s.sql_timeout_ms} "
            "-c idle_in_transaction_session_timeout=30000 "
            f"-c timezone={s.tz.key}"
        )},
    )


def message(exc: Exception) -> str:
    """Première ligne de l'erreur PostgreSQL (lisible, sans le SQL complet)."""
    orig = getattr(exc, "orig", exc)
    return str(orig).strip().splitlines()[0] if str(orig).strip() else exc.__class__.__name__


def explain_cost(sql: str, params: dict | None = None) -> float:
    with engine().connect() as conn:
        plan = conn.execute(text("EXPLAIN (FORMAT JSON) " + sql), params or {}).fetchone()[0]
    if isinstance(plan, str):
        plan = json.loads(plan)
    return float(plan[0]["Plan"]["Total Cost"])


def query(sql: str, params: dict | None = None) -> tuple[list[str], list[tuple], bool]:
    limit = get_settings().max_sql_rows
    with engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        rows = result.fetchmany(limit + 1)
    return columns, [tuple(r) for r in rows[:limit]], len(rows) > limit


def source_views() -> dict[str, tuple[str, ...]]:
    inspector = inspect(engine())
    return {
        schema: tuple(sorted(inspector.get_view_names(schema=schema), key=str.casefold))
        for schema in sorted(get_settings().allowed_schemas)
    }


@lru_cache(maxsize=None)
def view_columns(schema: str, view: str) -> tuple[tuple[str, str], ...]:
    try:
        inspector = inspect(engine())
        available = inspector.get_view_names(schema=schema)
        match = next((n for n in available if n.casefold() == view.casefold()), None)
        if match is None:
            raise ConfigurationError(
                f"La vue {schema}.{view} est introuvable dans la base "
                f"« {get_settings().src_url.database} ». Lancez `make views` puis `make validate`."
            )
        cols = inspector.get_columns(match, schema=schema)
    except SQLAlchemyError as exc:
        raise QueryError("Impossible de lire le schéma des vues approuvées.",
                         stage="introspection du schéma", details=message(exc)) from exc
    return tuple((c["name"], str(c["type"])) for c in cols)
