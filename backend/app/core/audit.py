"""Journal d'audit : une ligne JSON par question (qui, quoi, quel SQL)."""
from __future__ import annotations

import datetime as dt
import json
import logging

from app.core.config import get_settings

log = logging.getLogger("mhm.audit")


def audit(user: str, question: str, mode: str, stage: str | None, sql: str | None,
          rows: int | None) -> None:
    s = get_settings()
    record = {
        "ts": dt.datetime.now(s.tz).isoformat(timespec="seconds"),
        "user": user, "question": question, "mode": mode,
        "stage": stage, "sql": sql, "rows": rows,
    }
    try:
        s.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(s.audit_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        log.error("Impossible d'écrire le journal d'audit : %s", exc)
