"""Exemples de requêtes réservés au prompt text-to-SQL."""
from __future__ import annotations

import datetime as dt
import json
import re

from app.core.dictionary import approved_views
from app.domain.sql.validator import validate_sql
from app.infrastructure.db import analytics as db

EXAMPLES = (
    ("Combien de patients chez MHM ?",
     "SELECT COUNT(*) AS total_patients FROM analytics.v_patients_masked", {}),
    ("Admissions par tranche d'âge en 2026",
     "SELECT age_group, COUNT(*) AS admissions FROM analytics.v_visits "
     "WHERE visit_date >= :start AND visit_date < :end GROUP BY age_group "
     "ORDER BY CASE age_group WHEN '0-5' THEN 1 WHEN '6-11' THEN 2 "
     "WHEN '12-17' THEN 3 WHEN '18-23' THEN 4 WHEN '24-29' THEN 5 "
     "WHEN '30-35' THEN 6 WHEN '36-41' THEN 7 WHEN '42-46' THEN 8 "
     "WHEN '47-52' THEN 9 WHEN '53-58' THEN 10 WHEN '59-64' THEN 11 "
     "WHEN '65-70' THEN 12 WHEN '70+' THEN 13 ELSE 14 END",
     {"start": "2026-01-01", "end": "2027-01-01"}),
    ("Combien de femmes sont venues à Fianarantsoa le mois dernier ?",
     "SELECT COUNT(*) AS admissions FROM analytics.v_visits "
     "WHERE gender = :gender AND district ILIKE :place "
     "AND visit_date >= :start AND visit_date < :end",
     {"gender": "F", "place": "%Fianarantsoa%", "start": "2026-10-01", "end": "2026-11-01"}),
)


def prompt_examples() -> str:
    return "\n\n".join(
        f"Question : {question}\nJSON : {json.dumps({'sql': sql, 'params': params}, ensure_ascii=False)}"
        for question, sql, params in EXAMPLES)


def check_all(offline: bool = False) -> list[str]:
    """Valide les requêtes d'exemple et, si possible, les colonnes réelles."""
    errors = []
    views = set(approved_views())
    dates = {"start": dt.date(2026, 1, 1), "end": dt.date(2026, 2, 1),
             "gender": "F", "place": "%Fianarantsoa%"}
    for question, sql, params in EXAMPLES:
        try:
            names = set(re.findall(r"(?<!:):([A-Za-z_]\w*)", sql))
            validated = validate_sql(sql, views, names)
            if not offline:
                used = names
                values = {**dates, **params}
                db.explain_cost(validated, {name: values[name] for name in used})
        except Exception as exc:
            errors.append(f"{question} : {str(exc).splitlines()[0]}")
    return errors
