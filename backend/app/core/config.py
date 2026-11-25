"""Configuration : tout vient des variables d'environnement (fichier .env)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.engine import URL

ASSISTANT_NAME = "iA'mbovo"
ROOT = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # python-dotenv est optionnel
    pass


def _csv(name: str, default: str = "") -> frozenset[str]:
    return frozenset(s.strip().casefold() for s in os.getenv(name, default).split(",") if s.strip())


def _url(prefix: str, database: str, user: str) -> URL:
    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv(f"{prefix}_USER", user),
        password=os.getenv(f"{prefix}_PASSWORD", ""),
        host=os.getenv(f"{prefix}_HOST", "localhost"),
        port=int(os.getenv(f"{prefix}_PORT", "5432")),
        database=os.getenv(f"{prefix}_DB", database),
    )


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    llm_model: str
    embed_model: str
    num_ctx: int
    top_k: int
    min_score: float
    max_sql_rows: int
    max_result_chars: int
    sql_max_attempts: int
    max_question_chars: int
    max_context_chars: int
    sql_timeout_ms: int
    max_explain_cost: float
    mhm_debug: bool
    tz: ZoneInfo
    allowed_schemas: frozenset[str]
    src_url: URL
    vec_url: URL
    app_url: URL
    dictionary_path: Path
    metrics_path: Path
    prompts_dir: Path
    audit_log: Path
    auth_disabled: bool
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    dev_role: str
    login_max_attempts: int
    login_lock_minutes: int
    cors_origins: list[str]
    superset_url: str
    superset_public_url: str
    superset_username: str
    superset_password: str
    superset_timeout: float
    dashboards_path: Path
    kpis_path: Path


def _ollama_host() -> str:
    """Adresse d'Ollama. Si OLLAMA_HOST contient autre chose qu'une URL (clé Gemini placée là temporairement),
    on garde l'adresse locale par défaut : les embeddings BGE-M3 passent toujours par Ollama."""
    default = "http://localhost:11434"
    value = os.getenv("OLLAMA_HOST", default).strip()
    return value.rstrip("/") if value.startswith(("http://", "https://")) else default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        ollama_host=_ollama_host(),
        llm_model=os.getenv("LLM_MODEL", "llama3.2"),
        embed_model=os.getenv("EMBED_MODEL", "bge-m3"),
        num_ctx=int(os.getenv("NUM_CTX", "4096")),
        top_k=int(os.getenv("TOP_K", "4")),
        min_score=float(os.getenv("MIN_SCORE", "0.55")),
        max_sql_rows=50,
        max_result_chars=2500,
        sql_max_attempts=2,
        max_question_chars=2000,
        max_context_chars=7000,
        sql_timeout_ms=int(os.getenv("SQL_TIMEOUT_MS", "10000")),
        max_explain_cost=float(os.getenv("MAX_EXPLAIN_COST", "200000")),
        mhm_debug=os.getenv("MHM_DEBUG", "0") == "1",
        tz=ZoneInfo(os.getenv("APP_TZ", "Indian/Antananarivo")),
        allowed_schemas=_csv("SRC_ALLOWED_SCHEMAS", "analytics"),
        src_url=_url("SRC", "prod_mhm_ps", "chatbot_ro"),
        vec_url=_url("VEC", "medrag_kb", "rag_admin"),
        app_url=_url("APP", "ambovo_app", "ambovo_app"),
        dictionary_path=Path(os.getenv("DATA_DICTIONARY", ROOT / "config" / "data_dictionary.yaml")),
        metrics_path=Path(os.getenv("METRICS_FILE", ROOT / "config" / "metrics.yaml")),
        prompts_dir=ROOT / "config" / "prompts",
        audit_log=ROOT / os.getenv("AUDIT_LOG", "logs/audit_log.jsonl"),
        auth_disabled=os.getenv("AUTH_DISABLED", "0") == "1",
        jwt_secret=os.getenv("JWT_SECRET", ""),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "480")),
        dev_role=os.getenv("DEV_ROLE", "admin"),
        login_max_attempts=int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")),
        login_lock_minutes=int(os.getenv("LOGIN_LOCK_MINUTES", "15")),
        cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()],
        superset_url=os.getenv("SUPERSET_URL", "http://localhost:18088").rstrip("/"),
        # Adresse de Superset vue par le NAVIGATEUR (peut différer de SUPERSET_URL, vue par le backend)
        superset_public_url=(os.getenv("SUPERSET_PUBLIC_URL") or os.getenv("SUPERSET_URL", "http://localhost:18088")).rstrip("/"),
        superset_username=os.getenv("SUPERSET_USERNAME", ""),
        superset_password=os.getenv("SUPERSET_PASSWORD", ""),
        superset_timeout=float(os.getenv("SUPERSET_TIMEOUT", "10")),
        dashboards_path=Path(os.getenv("DASHBOARDS_FILE", ROOT / "config" / "dashboards.yaml")),
        kpis_path=Path(os.getenv("KPIS_FILE", ROOT / "config" / "kpis.yaml")),
    )


def debug_trace(event: str, **details) -> None:
    if get_settings().mhm_debug:
        import json

        payload = json.dumps(details, ensure_ascii=False, default=str)
        print(f"[{ASSISTANT_NAME} DEBUG] {event}: {payload}", file=sys.stderr, flush=True)
