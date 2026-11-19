"""Hachage des mots de passe (argon2id) : on ne stocke jamais le mot de passe lui-même."""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MIN_LENGTH = 10

_hasher = PasswordHasher()
# Hachage factice : quand le compte n'existe pas, on fait quand même le calcul pour que la
# réponse prenne le même temps (sinon on pourrait deviner quels emails existent).
_DUMMY_HASH = _hasher.hash("mot-de-passe-factice")


def check_strength(password: str) -> None:
    """Refuse les mots de passe trop courts (utilisé à la création d'un compte)."""
    if len(password) < MIN_LENGTH:
        raise ValueError(f"Le mot de passe doit contenir au moins {MIN_LENGTH} caractères.")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """True seulement si le mot de passe correspond. Ne lève jamais d'exception."""
    try:
        matches = _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False
    return matches and password_hash is not None
