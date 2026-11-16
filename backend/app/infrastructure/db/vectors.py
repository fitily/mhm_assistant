"""Base vectorielle (pgvector) : table documents_kb pour la recherche dans les PDF."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.errors import ConfigurationError

TABLE = "documents_kb"
DIM = 1024  # bge-m3


@lru_cache(maxsize=1)
def engine():
    url = get_settings().vec_url
    if not url.password:
        raise ConfigurationError("VEC_PASSWORD est requis pour accéder à la base documentaire.")
    return create_engine(url, pool_pre_ping=True)


def _literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


def ensure_table() -> None:
    with engine().begin() as conn:
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {TABLE} (id bigserial PRIMARY KEY, file_name text NOT NULL, "
            f"page int, content text NOT NULL, embedding vector({DIM}) NOT NULL)"))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS {TABLE}_hnsw ON {TABLE} "
            "USING hnsw (embedding vector_cosine_ops)"))


def ingested_files() -> set[str]:
    with engine().connect() as conn:
        return {r[0] for r in conn.execute(text(f"SELECT DISTINCT file_name FROM {TABLE}"))}


def add_chunks(rows: list[dict]) -> None:
    """rows : {file_name, page, content, embedding}."""
    with engine().begin() as conn:
        conn.execute(
            text(f"INSERT INTO {TABLE} (file_name, page, content, embedding) "
                 "VALUES (:file_name, :page, :content, CAST(:embedding AS vector))"),
            [{**r, "embedding": _literal(r["embedding"])} for r in rows])


def reset() -> None:
    with engine().begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))


def similar(vector: list[float], k: int) -> list[dict]:
    sql = (f"SELECT file_name, page, content, 1 - (embedding <=> CAST(:v AS vector)) AS score "
           f"FROM {TABLE} ORDER BY embedding <=> CAST(:v AS vector) LIMIT :k")
    with engine().connect() as conn:
        rows = conn.execute(text(sql), {"v": _literal(vector), "k": k}).mappings().all()
    return [dict(r) for r in rows]
