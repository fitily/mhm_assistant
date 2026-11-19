"""Base des utilisateurs (comptes et rôles). Base SÉPARÉE des données médicales."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.errors import ConfigurationError


@dataclass(frozen=True)
class UserRecord:
    id: int
    email: str
    full_name: str
    password_hash: str
    role: str
    is_active: bool


_COLUMNS = "id, email, full_name, password_hash, role, is_active"


@lru_cache(maxsize=1)
def engine():
    url = get_settings().app_url
    if not url.password:
        raise ConfigurationError("APP_PASSWORD est requis pour accéder à la base des utilisateurs.")
    return create_engine(url, pool_pre_ping=True)


def find_by_email(email: str) -> UserRecord | None:
    with engine().connect() as conn:
        row = conn.execute(
            text(f"SELECT {_COLUMNS} FROM users WHERE lower(email) = lower(:email)"),
            {"email": email.strip()}).mappings().first()
    return UserRecord(**row) if row else None


def create(email: str, full_name: str, password_hash: str, role: str) -> int:
    """Crée un compte et retourne son id. Lève ValueError si l'email existe déjà."""
    try:
        with engine().begin() as conn:
            return conn.execute(
                text("INSERT INTO users (email, full_name, password_hash, role) "
                     "VALUES (:email, :full_name, :password_hash, :role) RETURNING id"),
                {"email": email.strip().lower(), "full_name": full_name.strip(),
                 "password_hash": password_hash, "role": role}).scalar_one()
    except IntegrityError as exc:
        raise ValueError("Un compte existe déjà avec cet email.") from exc


def set_password_hash(email: str, password_hash: str) -> bool:
    """Remplace le mot de passe haché. Retourne False si le compte n'existe pas."""
    with engine().begin() as conn:
        result = conn.execute(
            text("UPDATE users SET password_hash = :h WHERE lower(email) = lower(:email)"),
            {"h": password_hash, "email": email.strip()})
    return result.rowcount > 0


def touch_last_login(user_id: int) -> None:
    with engine().begin() as conn:
        conn.execute(text("UPDATE users SET last_login_at = now() WHERE id = :id"), {"id": user_id})


def list_users() -> list[dict]:
    with engine().connect() as conn:
        rows = conn.execute(text(
            "SELECT email, full_name, role, is_active, last_login_at FROM users ORDER BY email"
        )).mappings().all()
    return [dict(r) for r in rows]
