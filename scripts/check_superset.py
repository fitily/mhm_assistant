"""Vérifie la liaison backend ↔ Superset (sans afficher aucun secret).

    python scripts/check_superset.py

Contrôle : configuration, connexion du compte technique, puis un jeton invité pour chaque dashboard du catalogue.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.errors import ConfigurationError, SupersetError  # noqa: E402
from app.core.security import Principal  # noqa: E402
from app.domain.dashboard_catalog import get_catalog  # noqa: E402
from app.services import superset_service  # noqa: E402


def main() -> int:
    s = get_settings()
    print(f"Superset : {s.superset_url}  |  compte technique : {s.superset_username or '(non défini)'}")
    try:
        dashboards = get_catalog().all()
        print(f"Catalogue : {len(dashboards)} dashboard(s) dans {s.dashboards_path.name}")
        checker = Principal("check-superset", "admin", "Check")
        failures = 0
        for d in dashboards:
            try:
                access = superset_service.create_guest_access(d.key, checker)
                print(f"  OK     {d.key:<10} {d.title}  (jeton de {len(access.token)} caractères, expire : {access.expires_at})")
            except SupersetError as exc:
                failures += 1
                print(f"  ÉCHEC  {d.key:<10} {d.title}  -> {exc}")
        return 1 if failures else 0
    except ConfigurationError as exc:
        print(f"Configuration : {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
