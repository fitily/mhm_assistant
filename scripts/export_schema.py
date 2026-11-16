"""Exporte les colonnes des vues analytics (aide pour remplir le dictionnaire de données).

    python scripts/export_schema.py > docs/schema_export.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.infrastructure.db.analytics import source_views, view_columns  # noqa: E402

for schema, names in source_views().items():
    for name in names:
        print(f"\n{schema}.{name}")
        for col, ctype in view_columns(schema, name):
            print(f"  - {col} ({ctype})")
