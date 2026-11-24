"""Indicateurs clés (KPI) de la page Analytics : catalogue (config/kpis.yaml) et calcul des périodes.

Le fichier de configuration ne contient AUCUN SQL : il désigne une vue et une colonne de date, et le code
(services/kpi_service.py) écrit lui-même la requête. Les périodes sont calculées ici, en Python pur (testable).
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.core.config import get_settings
from app.core.errors import ConfigurationError

KINDS = frozenset({"rolling_7_days", "monthly_trend"})
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class KpiDef:
    key: str
    label: str
    kind: str
    schema: str
    view: str
    date_column: str


@lru_cache(maxsize=1)
def get_kpi_defs() -> tuple[KpiDef, ...]:
    path = get_settings().kpis_path
    if not path.is_file():
        raise ConfigurationError(f"Fichier des indicateurs introuvable : {path}")
    try:
        raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("kpis") or []
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Fichier des indicateurs illisible : {exc}") from None
    defs, seen = [], set()
    for item in raw:
        try:
            key, label, kind = str(item["key"]), str(item["label"]), str(item["kind"])
            schema, _, view = str(item["view"]).partition(".")
            column = str(item["date_column"])
        except (KeyError, TypeError):
            raise ConfigurationError("Chaque indicateur doit avoir key, label, kind, view, date_column.") from None
        if not _KEY_RE.match(key) or key in seen:
            raise ConfigurationError(f"Clé d'indicateur invalide ou en double : {key!r}")
        if kind not in KINDS:
            raise ConfigurationError(f"Type d'indicateur inconnu pour {key} : {kind!r}")
        if not (_IDENT_RE.match(schema) and _IDENT_RE.match(view) and _IDENT_RE.match(column)):
            raise ConfigurationError(f"Vue ou colonne invalide pour l'indicateur {key}.")
        seen.add(key)
        defs.append(KpiDef(key, label, kind, schema, view, column))
    return tuple(defs)


# --- périodes : toujours [start, end[ (fin exclue) ---------------------------------------------------------------

def rolling_7_days(today: dt.date) -> tuple[dt.date, dt.date]:
    """Les 7 derniers jours, aujourd'hui inclus."""
    return today - dt.timedelta(days=6), today + dt.timedelta(days=1)


def month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    first = dt.date(year, month, 1)
    return first, first + dt.timedelta(days=calendar.monthrange(year, month)[1])


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def last_complete_month(reference: dt.date) -> tuple[tuple[int, int], tuple[int, int]]:
    """(dernier mois complet, mois précédent) vu depuis `reference` (dernière date des données).

    Si `reference` n'est pas le dernier jour de son mois, ce mois est incomplet : on prend le précédent.
    """
    _, end = month_bounds(reference.year, reference.month)
    current = (reference.year, reference.month)
    target = current if reference == end - dt.timedelta(days=1) else _previous_month(*current)
    return target, _previous_month(*target)
