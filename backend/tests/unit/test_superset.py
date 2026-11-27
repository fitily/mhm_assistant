"""Tests du catalogue de dashboards, du client Superset (faux serveur HTTP) et du service."""
import json
import time

import httpx
import jwt
import pytest

from app.core.errors import (
    ConfigurationError,
    SupersetAuthError,
    SupersetRejected,
    SupersetUnavailable,
)
from app.core.security import Principal
from app.domain.dashboard_catalog import DashboardCatalog, UnknownDashboard
from app.infrastructure.superset.client import SupersetClient
from app.services import superset_service

UUID_A = "b973604e-c78d-47ce-8fdf-876722c1aaed"
UUID_B = "7893e593-7f0c-481f-8326-8e2843abe736"
BASE = "http://superset.test"


# ----- Catalogue ----------------------------------------------------------------------------
def write_yaml(tmp_path, body):
    p = tmp_path / "dashboards.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_catalog_loads_and_looks_up_by_key(tmp_path):
    cat = DashboardCatalog.from_file(write_yaml(tmp_path, f"""
dashboards:
  - {{key: visite, title: Visites, uuid: "{UUID_A.upper()}"}}
  - {{key: medicale, title: Médical, uuid: {UUID_B}}}
"""))
    assert [d.key for d in cat.all()] == ["visite", "medicale"]
    assert cat.get("visite").uuid == UUID_A  # UUID normalisé en minuscules


def test_catalog_rejects_unknown_key(tmp_path):
    cat = DashboardCatalog.from_file(write_yaml(tmp_path, f"dashboards:\n  - {{key: visite, title: V, uuid: {UUID_A}}}\n"))
    with pytest.raises(UnknownDashboard):
        cat.get("../etc/passwd")


@pytest.mark.parametrize("entry", [
    "{key: Visite, title: V, uuid: %s}" % UUID_A,        # majuscule interdite
    "{key: visite, title: '', uuid: %s}" % UUID_A,       # titre vide
    "{key: visite, title: V, uuid: pas-un-uuid}",        # UUID invalide
])
def test_catalog_rejects_invalid_entries(tmp_path, entry):
    with pytest.raises(ConfigurationError):
        DashboardCatalog.from_file(write_yaml(tmp_path, f"dashboards:\n  - {entry}\n"))


def test_catalog_rejects_duplicates(tmp_path):
    body = f"dashboards:\n  - {{key: a1, title: A, uuid: {UUID_A}}}\n  - {{key: a1, title: B, uuid: {UUID_B}}}\n"
    with pytest.raises(ConfigurationError):
        DashboardCatalog.from_file(write_yaml(tmp_path, body))


def test_catalog_missing_file(tmp_path):
    with pytest.raises(ConfigurationError):
        DashboardCatalog.from_file(tmp_path / "absent.yaml")


def test_shipped_catalog_is_valid():
    from app.core.config import get_settings
    cat = DashboardCatalog.from_file(get_settings().dashboards_path)
    assert {"visite", "medicale"} <= {d.key for d in cat.all()}


# ----- Client -------------------------------------------------------------------------------
class FakeSuperset:
    """Imite les 3 appels de Superset et garde une trace des requêtes reçues."""

    def __init__(self, *, login=200, csrf=200, guest=200, valid_token="ACCESS"):
        self.codes = {"login": login, "csrf": csrf, "guest": guest}
        self.valid_token = valid_token
        self.calls: list[httpx.Request] = []
        self.logins = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path.endswith("/security/login"):
            self.logins += 1
            code = self.codes["login"]
            return httpx.Response(code, json={"access_token": self.valid_token} if code == 200 else {"message": "x"})
        if request.headers.get("authorization") != f"Bearer {self.valid_token}":
            return httpx.Response(401, json={"msg": "expired"})
        if path.endswith("/csrf_token/"):
            code = self.codes["csrf"]
            return httpx.Response(code, json={"result": "CSRF"} if code == 200 else {})
        if path.endswith("/guest_token/"):
            code = self.codes["guest"]
            return httpx.Response(code, json={"token": "GUEST"} if code == 200 else {"message": "nope"})
        return httpx.Response(404)


def make_client(fake, **kw):
    return SupersetClient(BASE, "svc", "secret-pw", transport=httpx.MockTransport(fake), **kw)


def test_guest_token_happy_path_and_request_shape():
    fake = FakeSuperset()
    token = make_client(fake).guest_token(UUID_A, username="admin@mhm.org", first_name="Fitily")
    assert token == "GUEST"
    login, _, post = fake.calls
    assert json.loads(login.content)["provider"] == "db"
    body = json.loads(post.content)
    assert body["resources"] == [{"type": "dashboard", "id": UUID_A}]  # un seul dashboard
    assert body["rls"] == []
    assert body["user"]["username"] == "admin@mhm.org"
    assert post.headers["x-csrftoken"] == "CSRF"


def test_access_token_is_reused_between_calls():
    fake = FakeSuperset()
    client = make_client(fake)
    client.guest_token(UUID_A, username="u")
    client.guest_token(UUID_B, username="u")
    assert fake.logins == 1


def test_relogin_once_when_access_token_expired():
    fake = FakeSuperset()
    client = make_client(fake)
    client._access_token, client._access_at = "OLD", time.monotonic()  # jeton périmé côté Superset
    assert client.guest_token(UUID_A, username="u") == "GUEST"
    assert fake.logins == 1


def test_wrong_backend_credentials():
    with pytest.raises(SupersetAuthError):
        make_client(FakeSuperset(login=401)).guest_token(UUID_A, username="u")


def test_insufficient_rights_on_guest_token():
    with pytest.raises(SupersetAuthError):
        make_client(FakeSuperset(guest=403)).guest_token(UUID_A, username="u")


def test_unknown_dashboard_is_rejected():
    with pytest.raises(SupersetRejected):
        make_client(FakeSuperset(guest=400)).guest_token(UUID_A, username="u")


def test_server_error_means_unavailable():
    with pytest.raises(SupersetUnavailable):
        make_client(FakeSuperset(login=503)).guest_token(UUID_A, username="u")


def test_network_failure_means_unavailable_and_leaks_nothing():
    def boom(request):
        raise httpx.ConnectError("refused on http://superset.test with secret-pw")

    with pytest.raises(SupersetUnavailable) as exc:
        SupersetClient(BASE, "svc", "secret-pw", transport=httpx.MockTransport(boom)).guest_token(UUID_A, username="u")
    assert "secret-pw" not in str(exc.value)


def test_timeout_means_unavailable():
    def slow(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(SupersetUnavailable):
        SupersetClient(BASE, "svc", "pw", transport=httpx.MockTransport(slow)).guest_token(UUID_A, username="u")


@pytest.mark.parametrize("args", [("", "svc", "pw"), (BASE, "", "pw"), (BASE, "svc", "")])
def test_client_requires_configuration(args):
    with pytest.raises(ConfigurationError):
        SupersetClient(*args)


# ----- Service ------------------------------------------------------------------------------
class StubClient:
    def __init__(self, token):
        self.token, self.seen = token, None

    def guest_token(self, uuid, **kw):
        self.seen = (uuid, kw)
        return self.token


def test_service_returns_dashboard_token_and_expiry():
    exp = int(time.time()) + 300
    stub = StubClient(jwt.encode({"exp": exp}, "k" * 40, algorithm="HS256"))
    access = superset_service.create_guest_access("visite", Principal("a@mhm.org", "admin", "Ada"), client=stub)
    assert access.dashboard.key == "visite"
    assert access.expires_at == exp
    assert stub.seen[0] == UUID_A
    assert stub.seen[1]["username"] == "a@mhm.org"


def test_service_tolerates_opaque_token():
    access = superset_service.create_guest_access("medicale", Principal("a@mhm.org", "admin"), client=StubClient("opaque"))
    assert access.expires_at is None


def test_service_refuses_key_outside_catalog_without_calling_superset():
    stub = StubClient("x")
    with pytest.raises(UnknownDashboard):
        superset_service.create_guest_access("inconnu", Principal("a@mhm.org", "admin"), client=stub)
    assert stub.seen is None


# ----- Noms des dashboards synchronisés avec Superset ----------------------------------------
class FakeSupersetDashboards:
    """Faux Superset : liste des dashboards + UUID d'intégration de chacun."""

    def __init__(self, dashboards, *, list_code=200):
        self.dashboards = dashboards  # {id: (titre, uuid d'intégration ou None)}
        self.list_code = list_code
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path.endswith("/security/login"):
            return httpx.Response(200, json={"access_token": "ACCESS"})
        if path == "/api/v1/dashboard/":
            if self.list_code != 200:
                return httpx.Response(self.list_code, json={})
            rows = [{"id": i, "dashboard_title": t} for i, (t, _) in self.dashboards.items()]
            return httpx.Response(200, json={"result": rows, "count": len(rows)})
        if path.endswith("/embedded"):
            did = int(path.split("/")[-2])
            emb = self.dashboards[did][1]
            return httpx.Response(200, json={"result": {"uuid": emb}}) if emb else httpx.Response(404, json={})
        return httpx.Response(404)


def test_client_reads_titles_by_embedded_uuid():
    fake = FakeSupersetDashboards({1: ("AI-assistant-dashboard", UUID_A.upper()), 2: ("Autre", None),
                                   3: ("HMH_Medical_Dashboard", UUID_B)})
    titles = make_client(fake).dashboard_titles([UUID_A, UUID_B])
    assert titles == {UUID_A: "AI-assistant-dashboard", UUID_B: "HMH_Medical_Dashboard"}


def test_client_titles_rights_error():
    with pytest.raises(SupersetAuthError):
        make_client(FakeSupersetDashboards({}, list_code=403)).dashboard_titles([UUID_A])


class StubTitles:
    def __init__(self, titles=None, error=None):
        self.titles, self.error, self.calls = titles or {}, error, 0

    def dashboard_titles(self, uuids):
        self.calls += 1
        if self.error:
            raise self.error
        return self.titles


@pytest.fixture
def fresh_cache():
    superset_service.clear_title_cache()
    yield
    superset_service.clear_title_cache()


def test_service_shows_superset_names_and_follows_renames(fresh_cache, monkeypatch):
    stub = StubTitles({UUID_A: "Nouveau nom Superset"})
    names = {d.key: d.title for d in superset_service.list_dashboards(client=stub)}
    assert names["visite"] == "Nouveau nom Superset"      # nom Superset
    assert names["medicale"] == "HMH_Medical_Dashboard"   # absent de Superset : repli sur le catalogue
    # résultat mis en cache ; après expiration, un renommage est repris
    superset_service.list_dashboards(client=stub)
    assert stub.calls == 1
    superset_service.clear_title_cache()
    stub.titles = {UUID_A: "Encore un autre nom"}
    assert superset_service.list_dashboards(client=stub)[0].title == "Encore un autre nom"


def test_service_falls_back_to_catalog_titles_when_superset_is_down(fresh_cache):
    stub = StubTitles(error=SupersetUnavailable("down"))
    titles = [d.title for d in superset_service.list_dashboards(client=stub)]
    assert titles == ["AI-assistant-dashboard", "HMH_Medical_Dashboard"]
    superset_service.list_dashboards(client=stub)
    assert stub.calls == 1  # pas de nouvel essai à chaque message


def test_service_without_sync_never_calls_superset(fresh_cache):
    stub = StubTitles({UUID_A: "X"})
    assert superset_service.list_dashboards(sync=False, client=stub)[0].title == "AI-assistant-dashboard"
    assert stub.calls == 0
