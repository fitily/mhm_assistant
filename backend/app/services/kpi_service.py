"""Calcul des indicateurs clés : requêtes COUNT(*) en lecture seule, isolées l'une de l'autre, avec cache.

 - rolling_7_days : valeur = nombre de lignes des 7 derniers jours (0 s'il n'y en a aucune).
 - monthly_trend  : dernier mois COMPLET des données + évolution (%) face au mois précédent.
Un indicateur qui échoue n'empêche pas les autres : il sort avec `error=True` (sans détail technique).
"""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.dictionary import approved_views
from app.core.errors import ConfigurationError
from app.domain import kpis
from app.domain.kpis import KpiDef
from app.infrastructure.db import analytics as db

log = logging.getLogger("mhm.kpi")

CACHE_SECONDS = 300
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December")
_cache: dict = {"t": 0.0, "day": None, "value": None}
_lock = threading.Lock()


@dataclass(frozen=True)
class KpiValue:
    key: str
    label: str
    value: int | None = None            # None = erreur (jamais 0 par défaut : un 0 doit être un vrai 0)
    hint: str = ""
    delta_percent: float | None = None  # monthly_trend : évolution face au mois précédent
    error: bool = False


def _month_label(year: int, month: int) -> str:
    return f"{_MONTHS[month - 1]} {year}"


def _count(defn: KpiDef, start: dt.date, end: dt.date) -> int:
    meta = approved_views().get((defn.schema.casefold(), defn.view.casefold()))
    if meta is None or defn.date_column.casefold() not in {c.casefold() for c in meta.get("columns", {})}:
        raise ConfigurationError(f"Indicateur {defn.key} : vue ou colonne absente du dictionnaire.")
    col = defn.date_column
    sql = f"SELECT COUNT(*) FROM {defn.schema}.{defn.view} WHERE {col} >= :start AND {col} < :end"
    _, rows, _ = db.query(sql, {"start": start, "end": end})
    return int(rows[0][0])


def _latest_data_date() -> dt.date | None:
    from app.domain.sql.executor import data_range  # import tardif : évite de charger sqlglot au démarrage
    try:
        rng = data_range()
    except Exception:  # noqa: BLE001 — information facultative
        return None
    return rng[1] if rng else None


def _rolling(defn: KpiDef, today: dt.date, latest: dt.date | None) -> KpiValue:
    start, end = kpis.rolling_7_days(today)
    value = _count(defn, start, end)
    last = end - dt.timedelta(days=1)
    hint = f"Last 7 days · {start:%d/%m} – {last:%d/%m/%Y}"
    if value == 0 and latest is not None and latest < start:
        hint += f" · latest data: {latest:%d/%m/%Y}"  # explique un 0 quand les données sont plus anciennes
    return KpiValue(defn.key, defn.label, value, hint)


def _monthly(defn: KpiDef, today: dt.date, latest: dt.date | None) -> KpiValue:
    (y, m), (py, pm) = kpis.last_complete_month(latest or today)
    current = _count(defn, *kpis.month_bounds(y, m))
    previous = _count(defn, *kpis.month_bounds(py, pm))
    delta = round((current - previous) / previous * 100, 1) if previous else None
    hint = f"{_month_label(y, m)} · vs {previous:,} in {_MONTHS[pm - 1]}".replace(",", " ")
    return KpiValue(defn.key, defn.label, current, hint, delta)


def _compute(today: dt.date) -> list[KpiValue]:
    latest = _latest_data_date()
    results = []
    for defn in kpis.get_kpi_defs():
        try:
            fn = _rolling if defn.kind == "rolling_7_days" else _monthly
            results.append(fn(defn, today, latest))
        except Exception as exc:  # noqa: BLE001 — un indicateur en panne ne bloque pas les autres
            log.error("Indicateur %s indisponible : %s", defn.key, type(exc).__name__)
            results.append(KpiValue(defn.key, defn.label, None, "Unavailable", None, True))
    return results


def get_kpis() -> list[KpiValue]:
    """Indicateurs (cache 5 min, renouvelé à minuit : « 7 derniers jours » dépend de la date du jour)."""
    today = dt.datetime.now(get_settings().tz).date()
    with _lock:
        fresh = _cache["value"] is not None and _cache["day"] == today \
            and time.monotonic() - _cache["t"] < CACHE_SECONDS
        if fresh:
            return _cache["value"]
        values = _compute(today)
        if not any(v.error for v in values):  # on ne garde pas en cache un résultat partiellement en panne
            _cache.update(t=time.monotonic(), day=today, value=values)
        return values


def clear_cache() -> None:
    _cache.update(t=0.0, day=None, value=None)
