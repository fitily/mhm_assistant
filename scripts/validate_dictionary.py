"""Vérifie que config/data_dictionary.yaml correspond aux vues réelles de PostgreSQL.

    python scripts/validate_dictionary.py            # avec la base
    python scripts/validate_dictionary.py --offline  # structure du YAML seulement
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.dictionary import approved_views, dictionary  # noqa: E402
from app.domain.sql.examples import check_all  # noqa: E402


def main(offline: bool) -> int:
    errors: list[str] = []
    views = approved_views()
    for (schema, name), meta in views.items():
        for key in ("description", "keywords"):
            if not meta.get(key):
                errors.append(f"{schema}.{name} : « {key} » manquant")
    if offline:
        print(f"{len(views)} vues déclarées (mode hors ligne).")
    else:
        from app.infrastructure.db.analytics import view_columns

        for (schema, name), meta in views.items():
            try:
                real = {c.casefold() for c, _ in view_columns(schema, name)}
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{schema}.{name} : {exc}")
                continue
            for col in (meta.get("columns") or {}):
                if col.casefold() not in real:
                    errors.append(f"{schema}.{name} : colonne documentée « {col} » absente de la base")
            if meta.get("date_column") and meta["date_column"].casefold() not in real:
                errors.append(f"{schema}.{name} : date_column « {meta['date_column']} » absente")
            undocumented = real - {c.casefold() for c in (meta.get("columns") or {})}
            if undocumented:
                print(f"  note : {schema}.{name} colonnes non documentées : {sorted(undocumented)}")
    if not dictionary().get("glossary"):
        errors.append("config/metrics.yaml : « definitions » vide")
    errors.extend(f"Exemple SQL : {e}" for e in check_all(offline=offline))
    for e in errors:
        print("ERREUR :", e)
    print("OK" if not errors else f"{len(errors)} erreur(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main("--offline" in sys.argv))
