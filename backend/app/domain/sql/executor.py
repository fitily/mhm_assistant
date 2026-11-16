"""Exécution : contrôle de la période, boucle génération → validation → EXPLAIN → exécution."""
from __future__ import annotations

import datetime as dt
import time
from decimal import Decimal

import sqlglot
from sqlalchemy.exc import SQLAlchemyError
from sqlglot import exp

from app.core.config import get_settings
from app.core.dictionary import dictionary
from app.core.errors import ConfigurationError, OutOfRange, QueryError
from app.domain.models import Period, SQLRun
from app.domain.periods import normalize_question
from app.domain.sql import generator
from app.domain.sql.validator import validate_sql
from app.infrastructure.db import analytics as db

_RANGE_CACHE: dict[str, object] = {"t": 0.0, "value": None}


def _to_date(value) -> dt.date | None:
    if isinstance(value, dt.datetime):
        tz = get_settings().tz
        return value.astimezone(tz).date() if value.tzinfo else value.date()
    return value if isinstance(value, dt.date) else None


def data_range() -> tuple[dt.date, dt.date] | None:
    """Plage min/max des données (cache 5 min). None si inconnue."""
    cfg = dictionary().get("data_freshness")
    if not cfg:
        return None
    if time.monotonic() - float(_RANGE_CACHE["t"]) < 300 and _RANGE_CACHE["value"]:
        return _RANGE_CACHE["value"]  # type: ignore[return-value]
    schema, _, view = str(cfg["view"]).partition(".")
    column = str(cfg["column"])
    if not (schema.isidentifier() and view.isidentifier() and column.isidentifier()):
        raise ConfigurationError("data_freshness du dictionnaire invalide.")
    if column.casefold() not in {n.casefold() for n, _ in db.view_columns(schema, view)}:
        raise ConfigurationError(f"La colonne de fraîcheur {schema}.{view}.{column} n'existe pas.")
    try:
        _, rows, _ = db.query(f"SELECT min({column}), max({column}) FROM {schema}.{view}")
    except SQLAlchemyError as exc:
        raise QueryError("Impossible de vérifier la couverture des données.",
                         stage="fraîcheur des données", details=db.message(exc)) from exc
    lo, hi = (_to_date(v) for v in rows[0]) if rows else (None, None)
    if lo is None or hi is None:
        return None
    _RANGE_CACHE.update(t=time.monotonic(), value=(lo, hi))
    return lo, hi


def check_range(period: Period | None, today: dt.date) -> list[str]:
    """Refuse une période hors données (OutOfRange) ; sinon retourne des notes."""
    rng = data_range()
    if not rng:
        return []
    lo, hi = rng
    notes: list[str] = []
    if period:
        if period.start > hi or period.end <= lo:
            raise OutOfRange(
                f"Les données disponibles couvrent du {lo:%d/%m/%Y} au {hi:%d/%m/%Y} ; la période "
                f"demandée ({period.label}) est hors de cette plage. Aucune requête n'a été "
                "exécutée, pour éviter un « 0 » trompeur.")
        if period.end - dt.timedelta(days=1) > hi:
            notes.append(f"Période partielle : les données s'arrêtent au {hi:%d/%m/%Y}.")
    if not period and hi < today - dt.timedelta(days=7):
        notes.append(f"Données disponibles jusqu'au {hi:%d/%m/%Y}.")
    return notes


def generic_notes(run: SQLRun) -> list[str]:
    """Contrôles valables pour toute requête (résultat vide, zéro, tronqué)."""
    notes: list[str] = []
    if not run.rows:
        notes.append("Aucune ligne ne correspond. Ce n'est pas forcément « 0 » : vérifiez la "
                     "période, les filtres et la couverture des données.")
    elif len(run.rows) == 1 and len(run.rows[0]) == 1 and run.rows[0][0] in (0, Decimal(0)):
        notes.append("Le résultat est 0 : contrôlez les filtres (un libellé en anglais, une "
                     "période couverte ?) avant de conclure à l'absence de cas.")
    if run.truncated:
        notes.append(f"Résultat limité aux {get_settings().max_sql_rows} premières lignes.")
    return notes


def sql_notes(run: SQLRun, views: dict) -> list[str]:
    """Notes liées aux colonnes fragiles et aux vues utilisées par le SQL généré."""
    tree = sqlglot.parse_one(run.sql, read="postgres")
    cols = {c.name.casefold() for c in tree.find_all(exp.Column)}
    notes = [" ".join(str(n).split()) for c, n in (dictionary().get("fragile_columns") or {}).items()
             if c.casefold() in cols]
    for t in tree.find_all(exp.Table):
        note = (views.get((t.db.casefold(), t.name.casefold())) or {}).get("answer_note")
        if note:
            notes.append(str(note))
    return notes


def run_sql(question: str, views: dict, history, period: Period | None) -> SQLRun:
    s = get_settings()
    today = dt.datetime.now(s.tz).date()
    normalized = normalize_question(question)
    notes = check_range(period, today)

    selected = generator.select_views(normalized, views)
    schema_txt, hint = generator.schema_prompt(selected), generator.period_hint(period, selected)

    correction, failures, last_sql, last_stage = "", [], "", "génération SQL"
    for attempt in range(s.sql_max_attempts):
        stage = "génération SQL"
        try:
            generated, generated_params = generator.generate(
                normalized, history, today, schema_txt, hint, correction)
            params = dict(generated_params)
            if period:
                params.update(start=period.start, end=period.end)
            last_sql, stage = generated, "validation SQL"
            validated = validate_sql(generated, set(views), set(params))
            last_sql, stage = validated, "EXPLAIN"
            cost = db.explain_cost(validated, params)
            if cost > s.max_explain_cost:
                raise ValueError(f"Requête trop coûteuse (coût estimé {cost:,.0f}). Ajoutez des filtres.")
            stage = "exécution"
            columns, rows, truncated = db.query(validated, params)
            run = SQLRun(validated, columns, rows, truncated, notes)
            run.notes.extend(generic_notes(run) + sql_notes(run, views))
            run.notes = list(dict.fromkeys(run.notes))
            return run
        except (SQLAlchemyError, ValueError) as exc:
            msg = db.message(exc) if isinstance(exc, SQLAlchemyError) else str(exc)
            failures.append(f"Tentative {attempt + 1} ({stage}) : {msg}")
            last_stage = stage
            correction = (f"La tentative précédente a échoué ({stage}) : {msg}\n"
                          "Retourne un objet JSON avec sql et params. Le champ sql doit contenir "
                          "un SELECT PostgreSQL normal, pas une agrégation JSON. Utilise seulement "
                          "les colonnes listées et lie chaque valeur de filtre.")
    raise QueryError(f"L'analyse a échoué après {s.sql_max_attempts} tentatives sécurisées.",
                     stage=last_stage, sql=last_sql or None, details="\n".join(failures))
