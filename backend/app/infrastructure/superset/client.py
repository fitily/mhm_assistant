"""Client HTTP minimal pour l'API de Superset : uniquement ce dont on a besoin (jeton invité).

Fonctionnement : le backend se connecte à Superset avec un compte technique (moindre privilège),
puis demande un « guest token » limité à UN dashboard et de courte durée (réglé côté Superset,
GUEST_TOKEN_JWT_EXP_SECONDS). C'est ce jeton, et lui seul, qui part vers le navigateur.

Sécurité : ni mot de passe ni jeton n'apparaissent dans les messages d'erreur ou les journaux.
"""
from __future__ import annotations

import threading
import time

import httpx

from app.core.errors import (
    ConfigurationError,
    SupersetAuthError,
    SupersetRejected,
    SupersetUnavailable,
)

ACCESS_TOKEN_TTL = 600.0  # on réutilise la connexion ~10 min (le jeton d'accès Superset dure 15 min)


class _Unauthorized(Exception):
    """Jeton d'accès expiré ou invalide : une nouvelle connexion peut régler le problème."""


class SupersetClient:
    def __init__(self, base_url: str, username: str, password: str, *, timeout: float = 10.0,
                 transport: httpx.BaseTransport | None = None):
        if not (base_url and username and password):
            raise ConfigurationError(
                "Superset n'est pas configuré : renseigner SUPERSET_URL, SUPERSET_USERNAME "
                "et SUPERSET_PASSWORD dans le fichier .env."
            )
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._transport = transport
        self._access_token: str | None = None
        self._access_at = 0.0
        self._lock = threading.Lock()

    # ----- API publique -----------------------------------------------------------------------
    def guest_token(self, dashboard_uuid: str, *, username: str, first_name: str = "",
                    last_name: str = "") -> str:
        """Jeton invité valable pour ce seul dashboard. Une reconnexion automatique est tentée une fois."""
        for attempt in (1, 2):
            access = self._access(force=attempt == 2)
            try:
                return self._request_guest_token(access, dashboard_uuid, username, first_name, last_name)
            except _Unauthorized:
                self._forget()
        raise SupersetAuthError("Superset refuse la connexion du compte technique du backend.")

    # ----- Connexion --------------------------------------------------------------------------
    def _access(self, *, force: bool = False) -> str:
        with self._lock:
            fresh = self._access_token and (time.monotonic() - self._access_at) < ACCESS_TOKEN_TTL
            if force or not fresh:
                self._access_token = self._login()
                self._access_at = time.monotonic()
            return self._access_token

    def _forget(self) -> None:
        with self._lock:
            self._access_token = None

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, timeout=self._timeout, transport=self._transport)

    def _login(self) -> str:
        body = {"username": self._username, "password": self._password, "provider": "db", "refresh": False}
        with self._client() as http:
            resp = self._send(http, "POST", "/api/v1/security/login", json=body)
        if resp.status_code in (400, 401, 403, 422):
            raise SupersetAuthError("Superset refuse les identifiants du compte technique du backend.")
        self._raise_for_server(resp)
        token = _json(resp).get("access_token")
        if not token:
            raise SupersetUnavailable("Réponse de connexion Superset inattendue.")
        return token

    # ----- Jeton invité -----------------------------------------------------------------------
    def _request_guest_token(self, access: str, dashboard_uuid: str, username: str,
                             first_name: str, last_name: str) -> str:
        auth = {"Authorization": f"Bearer {access}"}
        with self._client() as http:  # même session pour le jeton CSRF et la demande qui suit
            csrf_resp = self._send(http, "GET", "/api/v1/security/csrf_token/", headers=auth)
            self._check(csrf_resp, "obtenir le jeton CSRF")
            csrf = _json(csrf_resp).get("result")
            if not csrf:
                raise SupersetUnavailable("Réponse CSRF Superset inattendue.")

            payload = {
                "user": {"username": username, "first_name": first_name, "last_name": last_name},
                "resources": [{"type": "dashboard", "id": dashboard_uuid}],
                "rls": [],
            }
            headers = {**auth, "X-CSRFToken": csrf, "Referer": self._base_url}
            resp = self._send(http, "POST", "/api/v1/security/guest_token/", json=payload, headers=headers)
            self._check(resp, "créer le jeton invité")

        token = _json(resp).get("token")
        if not token:
            raise SupersetUnavailable("Réponse de jeton invité Superset inattendue.")
        return token

    # ----- Utilitaires ------------------------------------------------------------------------
    @staticmethod
    def _send(http: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return http.request(method, url, **kwargs)
        except httpx.TimeoutException:
            raise SupersetUnavailable("Superset ne répond pas (délai dépassé).") from None
        except httpx.HTTPError:
            raise SupersetUnavailable("Superset est injoignable.") from None

    @staticmethod
    def _raise_for_server(resp: httpx.Response) -> None:
        if resp.status_code >= 500:
            raise SupersetUnavailable(f"Superset a renvoyé une erreur serveur ({resp.status_code}).")

    def _check(self, resp: httpx.Response, action: str) -> None:
        if resp.status_code == 401:
            raise _Unauthorized
        if resp.status_code == 403:
            raise SupersetAuthError(f"Le compte technique n'a pas le droit de {action}.")
        if resp.status_code in (400, 404, 422):
            raise SupersetRejected(f"Superset a refusé de {action} (code {resp.status_code}).")
        self._raise_for_server(resp)
        if resp.status_code >= 400:
            raise SupersetRejected(f"Superset a refusé de {action} (code {resp.status_code}).")


def _json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
