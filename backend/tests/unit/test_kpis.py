"""Indicateurs clés : périodes, calcul (base simulée), isolation des pannes, cache et droits d'accès."""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import get_settings
from app.domain import kpis
from app.main import create_app
from app.services import auth_service, kpi_service

D = dt.date


# --- périodes --------------------------------------------------------------------------------------------------

def test_rolling_window_is_seven_days_including_today():
    start, end = kpis.rolling_7_days(D(2026, 11, 24))
    assert (start, end) == (D(2026, 11, 18), D(2026, 11, 25))
    assert (end - start).days == 7


def test_rolling_window_crosses_month_and_year():
    assert kpis.rolling_7_days(D(2027, 1, 3))[0] == D(2026, 12, 28)


@pytest.mark.parametrize("reference,target,previous", [
    (D(2026, 9, 16), (2026, 8), (2026, 7)),    # septembre incomplet -> août (votre cas)
    (D(2026, 9, 30), (2026, 9), (2026, 8)),    # dernier jour du mois -> ce mois est complet
    (D(2026, 1, 10), (2025, 12), (2025, 11)),  # passage d'année
    (D(2026, 3, 1), (2026, 2), (2026, 1)),
])
def test_last_complete_month(reference, target, previous):
    assert kpis.last_complete_month(reference) == (target, previous)


def test_august_includes_the_31st():
    """La requête de contrôle `< '2026-08-31'` oubliait le 31 août ; ici la fin est le 1er septembre (exclu)."""
    assert kpis.month_bounds(2026, 8) == (D(2026, 8, 1), D(2026, 9, 1))
    assert kpis.month_bounds(2028, 2)[1] == D(2028, 3, 1)  # année bissextile


# --- calcul ----------------------------------------------------------------------------------------------------

@pytest.fixture
def fake(monkeypatch):
    state = {"calls": [], "counts": {}, "fail": set(), "latest": D(2026, 9, 16)}

    def query(sql, params=None):
        state["calls"].append((sql, params))
        for name in state["fail"]:
            if name in sql:
                raise RuntimeError("base indisponible : secret-ne-doit-pas-sortir")
        key = (("v_visits" if "v_visits" in sql else "v_patients_masked"), params["start"])
        return ["count"], [(state["counts"].get(key, 0),)], False

    monkeypatch.setattr(kpi_service.db, "query", query)
    monkeypatch.setattr(kpi_service, "_latest_data_date", lambda: state["latest"])
    kpi_service.clear_cache()
    yield state
    kpi_service.clear_cache()


def _by_key(values):
    return {v.key: v for v in values}


def test_zero_is_shown_as_zero_with_explanation(fake):
    values = _by_key(kpi_service._compute(D(2026, 11, 24)))
    assert values["new_patients_7d"].value == 0 and values["admissions_7d"].value == 0
    assert "latest data: 16/09/2026" in values["admissions_7d"].hint
    assert not values["admissions_7d"].error


def test_weekly_counts_use_the_seven_day_window(fake):
    fake["counts"][("v_visits", D(2026, 11, 18))] = 12
    fake["counts"][("v_patients_masked", D(2026, 11, 18))] = 5
    values = _by_key(kpi_service._compute(D(2026, 11, 24)))
    assert values["admissions_7d"].value == 12 and values["new_patients_7d"].value == 5
    assert "latest data" not in values["admissions_7d"].hint or values["admissions_7d"].value == 0


def test_monthly_trend_compares_with_previous_month(fake):
    fake["counts"][("v_visits", D(2026, 8, 1))] = 3900
    fake["counts"][("v_visits", D(2026, 7, 1))] = 3600
    visits = _by_key(kpi_service._compute(D(2026, 11, 24)))["visits_last_month"]
    assert visits.value == 3900 and visits.delta_percent == 8.3
    assert visits.hint.startswith("August 2026")
    sql, params = [c for c in fake["calls"] if c[1]["start"] == D(2026, 8, 1)][0]
    assert params["end"] == D(2026, 9, 1)  # le 31 août est bien compté


def test_trend_without_previous_month_has_no_percentage(fake):
    fake["counts"][("v_visits", D(2026, 8, 1))] = 10
    assert _by_key(kpi_service._compute(D(2026, 11, 24)))["visits_last_month"].delta_percent is None


def test_one_failing_indicator_does_not_break_the_others(fake):
    fake["fail"].add("v_patients_masked")
    values = _by_key(kpi_service._compute(D(2026, 11, 24)))
    assert values["new_patients_7d"].error and values["new_patients_7d"].value is None  # jamais un faux 0
    assert not values["admissions_7d"].error
    assert "secret" not in repr(values["new_patients_7d"])


def test_queries_are_read_only_counts_with_bound_parameters(fake):
    kpi_service._compute(D(2026, 11, 24))
    for sql, params in fake["calls"]:
        assert sql.startswith("SELECT COUNT(*) FROM analytics.v_") and ":start" in sql and ":end" in sql
        assert set(params) == {"start", "end"}


def test_results_are_cached_but_not_when_partially_failing(fake):
    kpi_service.get_kpis()
    n = len(fake["calls"])
    kpi_service.get_kpis()
    assert len(fake["calls"]) == n
    kpi_service.clear_cache()
    fake["fail"].add("v_visits")
    kpi_service.get_kpis()
    n = len(fake["calls"])
    kpi_service.get_kpis()
    assert len(fake["calls"]) > n  # le résultat en panne n'est pas gardé : on réessaie


# --- API et droits -----------------------------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, tmp_path, fake):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("JWT_SECRET", "s" * 48)
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    auth_service.throttle.clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def _auth(role):
    token, _ = security.create_access_token(subject=f"{role}@mhm.org", role=role, name="Test")
    return {"Authorization": f"Bearer {token}"}


def test_admin_gets_the_three_indicators(client):
    r = client.get("/v1/kpis", headers=_auth("admin"))
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert [k["key"] for k in r.json()] == ["new_patients_7d", "admissions_7d", "visits_last_month"]
    assert all(k["value"] == 0 for k in r.json())


def test_doctor_and_anonymous_are_refused(client):
    assert client.get("/v1/kpis", headers=_auth("doctor")).status_code == 403
    assert client.get("/v1/kpis").status_code == 401


def test_invalid_configuration_gives_503_without_details(client, monkeypatch, tmp_path):
    bad = tmp_path / "kpis.yaml"
    bad.write_text("kpis:\n  - {key: x1, label: X, kind: inconnu, view: analytics.v_visits, date_column: visit_date}\n")
    monkeypatch.setenv("KPIS_FILE", str(bad))
    get_settings.cache_clear()
    kpis.get_kpi_defs.cache_clear()
    try:
        r = client.get("/v1/kpis", headers=_auth("admin"))
        assert r.status_code == 503 and "inconnu" not in r.text
    finally:
        get_settings.cache_clear()
        kpis.get_kpi_defs.cache_clear()
