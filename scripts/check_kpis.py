"""Affiche les indicateurs clés calculés sur la VRAIE base, pour les comparer à des chiffres que vous connaissez.

    python scripts/check_kpis.py

Aucun secret n'est affiché. Compare aussi le mois d'août 2026 avec la requête de contrôle corrigée
(fin exclue = 1er septembre, pour compter le 31 août).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.errors import ConfigurationError  # noqa: E402
from app.infrastructure.db import analytics as db  # noqa: E402
from app.services import kpi_service  # noqa: E402


def main() -> int:
    try:
        values = kpi_service.get_kpis()
    except ConfigurationError as exc:
        print(f"ERREUR de configuration : {exc}")
        return 1
    for v in values:
        shown = "INDISPONIBLE" if v.value is None else f"{v.value:,}".replace(",", " ")
        trend = "" if v.delta_percent is None else f"  ({v.delta_percent:+.1f} %)"
        print(f"{v.key:20} {shown:>10}{trend}   {v.hint}")
    try:
        _, rows, _ = db.query("SELECT COUNT(*) FROM analytics.v_visits "
                              "WHERE visit_date >= '2026-08-01' AND visit_date < '2026-09-01'")
        print(f"\nContrôle : visites du 01/08/2026 au 31/08/2026 inclus = {rows[0][0]:,}".replace(",", " "))
    except Exception as exc:  # noqa: BLE001
        print(f"\nContrôle impossible : {type(exc).__name__}")
    return 1 if any(v.error for v in values) else 0


if __name__ == "__main__":
    raise SystemExit(main())
