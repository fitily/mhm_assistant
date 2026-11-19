"""Connexion : vérifie le mot de passe, limite les essais ratés et émet le jeton."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.core import passwords, security
from app.core.audit import audit
from app.core.config import get_settings
from app.infrastructure.db import users


class InvalidCredentials(Exception):
    """Email inconnu, mot de passe faux ou compte désactivé (on ne précise jamais lequel)."""


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        super().__init__(f"Réessayez dans {retry_after} s.")
        self.retry_after = retry_after


@dataclass(frozen=True)
class LoginResult:
    token: str
    expires_in: int
    email: str
    name: str
    role: str


class LoginThrottle:
    """Bloque un identifiant après trop d'échecs récents (fenêtre glissante, en mémoire).

    Limite : la mémoire est propre à ce processus ; un redémarrage la remet à zéro.
    """

    MAX_KEYS = 1000

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _window(self) -> float:
        return get_settings().login_lock_minutes * 60

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self._window()]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def blocked_for(self, key: str) -> int:
        """Secondes restantes avant de pouvoir réessayer (0 si l'identifiant n'est pas bloqué)."""
        now = self._clock()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) < get_settings().login_max_attempts:
                return 0
            return max(1, int(self._window() - (now - recent[0])) + 1)

    def record_failure(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            if len(self._failures) >= self.MAX_KEYS:
                for stale in list(self._failures):
                    self._recent(stale, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


throttle = LoginThrottle()


def login(username: str, password: str) -> LoginResult:
    key = username.strip().casefold()
    wait = throttle.blocked_for(key)
    if wait:
        audit("inconnu", "(connexion)", "AUTH", "login_blocked", None, None)
        raise TooManyAttempts(wait)

    user = users.find_by_email(key)
    password_ok = passwords.verify_password(user.password_hash if user else None, password)
    if not (user and password_ok and user.is_active):
        throttle.record_failure(key)
        audit(user.email if user else "inconnu", "(connexion)", "AUTH", "login_failed", None, None)
        raise InvalidCredentials

    throttle.reset(key)
    users.touch_last_login(user.id)
    token, expires_in = security.create_access_token(
        subject=user.email, role=user.role, name=user.full_name)
    audit(user.email, "(connexion)", "AUTH", "login_ok", None, None)
    return LoginResult(token, expires_in, user.email, user.full_name, user.role)
