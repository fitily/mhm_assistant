"""Valeurs réelles des colonnes à peu de valeurs (gender, age_group) et corrections du SQL généré.

Utilisation : `sql, err = values.apply_all(sql)` avant l'EXPLAIN et l'exécution.
  err = None  → exécuter `sql` (éventuellement corrigé)
  err = texte → ne pas exécuter ; renvoyer `err` au LLM pour UNE nouvelle tentative.
"""
from __future__ import annotations

import re

from app.infrastructure.db import analytics as db

_cache: dict[str, list[str]] = {}
_VIEW_OK = re.compile(r"^analytics\.v_[a-z_]+$")
_COL_OK = re.compile(r"^[a-z_]+$")
_VIEW_IN_SQL = re.compile(r"\banalytics\.(v_[a-z_]+)", re.I)

GENDER_ALIASES = {
    "m": "M", "male": "M", "males": "M", "masculin": "M", "homme": "M", "hommes": "M",
    "man": "M", "men": "M", "boy": "M", "boys": "M", "garçon": "M", "garçons": "M", "garcon": "M",
    "garcons": "M",
    "f": "F", "female": "F", "females": "F", "feminin": "F", "féminin": "F", "femme": "F",
    "femmes": "F", "woman": "F", "women": "F", "girl": "F", "girls": "F", "fille": "F",
    "filles": "F",
}

# gender = 'F', gender ILIKE '%fem%', gender <> 'M', gender NOT ILIKE 'M'…
_FILTER = re.compile(
    r"\b(gender|age_group)\s*(NOT\s+ILIKE|NOT\s+LIKE|ILIKE|LIKE|<>|!=|=)\s*'%?([^'%]*)%?'", re.I)


def view_of(sql: str) -> str | None:
    """Première vue analytics citée dans le SQL (les requêtes actuelles n'en utilisent qu'une)."""
    m = _VIEW_IN_SQL.search(sql)
    return f"analytics.{m.group(1).lower()}" if m else None


def known_values(view: str, column: str, limit: int = 30) -> list[str]:
    """Valeurs distinctes d'une colonne. Liste vide si la vue ou la colonne est inconnue :
    dans ce cas on ne bloque rien (le SQL est vérifié par ailleurs)."""
    if not (_VIEW_OK.match(view) and _COL_OK.match(column)):
        return []
    key = f"{view}.{column}"
    if key not in _cache:
        try:
            _, rows, _ = db.query(
                f"SELECT DISTINCT {column} FROM {view} WHERE {column} IS NOT NULL "
                f"ORDER BY 1 LIMIT {int(limit)}", {})
        except Exception:        # colonne absente de cette vue, base indisponible…
            return []            # pas de mise en cache : on réessaiera
        _cache[key] = [str(r[0]) for r in rows]
    return _cache[key]


def fix_filters(sql: str, view: str) -> tuple[str, str | None]:
    """Remplace un filtre sur gender/age_group par la vraie valeur (égalité exacte).
    Renvoie (sql corrigé, erreur). erreur != None : valeur inconnue, à renvoyer au LLM."""
    error: str | None = None

    def repl(m: re.Match) -> str:
        nonlocal error
        col, op, literal = m.group(1).lower(), m.group(2).upper(), m.group(3).strip()
        valid = known_values(view, col)
        if not valid:
            return m.group(0)                       # impossible de vérifier : on laisse
        exact = next((v for v in valid if v.casefold() == literal.casefold()), None)
        if exact is None and col == "gender":
            alias = GENDER_ALIASES.get(literal.casefold())
            exact = alias if alias in valid else None
        if exact is None:
            error = error or (f"Valeur inconnue '{literal}' pour {col}. "
                              f"Valeurs possibles : {', '.join(valid)}.")
            return m.group(0)
        negative = op.startswith("NOT") or op in ("<>", "!=")
        return f"{col} {'<>' if negative else '='} '{exact.replace(chr(39), chr(39) * 2)}'"

    return _FILTER.sub(repl, sql), error


# Colonnes qui décrivent un groupe (sexe, âge, lieu) : compter leurs valeurs distinctes
# ne compte pas des patients. Valeurs = mots de l'alias qui montrent que c'est voulu
# (« COUNT(DISTINCT district) AS nb_districts » répond à « combien de districts »).
_CATEGORY_STEMS = {
    "gender": ("gender", "sexe"),
    "age_group": ("age_group", "tranche"),
    "district": ("district",),
    "commune": ("commune",),
    "category": ("categor",),
}
_DISTINCT_CAT = re.compile(
    rf"COUNT\s*\(\s*DISTINCT\s+(?:\w+\.)?({'|'.join(_CATEGORY_STEMS)})\s*\)(?:\s+AS\s+(\w+))?", re.I)


def fix_count_distinct(sql: str) -> tuple[str, str | None]:
    """COUNT(DISTINCT gender) AS distinct_patients compte des valeurs (1), pas des patients.
    - alias contenant « patient » : remplacé par COUNT(DISTINCT patient_key) ;
    - alias qui nomme la colonne (nb_districts) : conservé, c'est une question légitime ;
    - sinon : erreur pour une nouvelle tentative du LLM."""
    error: str | None = None

    def repl(m: re.Match) -> str:
        nonlocal error
        col, alias = m.group(1).lower(), m.group(2) or ""
        low = alias.lower()
        if any(stem in low for stem in _CATEGORY_STEMS[col]):
            return m.group(0)
        if "patient" in low:
            return f"COUNT(DISTINCT patient_key) AS {alias}"
        error = error or (f"COUNT(DISTINCT {col}) compte les valeurs de {col}, pas des patients. "
                          "Pour compter des patients, utilise COUNT(DISTINCT patient_key).")
        return m.group(0)

    return _DISTINCT_CAT.sub(repl, sql), error


def apply_all(sql: str, view: str | None = None) -> tuple[str, str | None]:
    """Point d'entrée unique pour le validator."""
    view = view or view_of(sql)
    err = None
    if view:
        sql, err = fix_filters(sql, view)
    if not err:
        sql, err = fix_count_distinct(sql)
    return sql, err