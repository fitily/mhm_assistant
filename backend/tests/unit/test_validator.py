import pytest

from app.domain.sql.validator import validate_sql

VIEWS = {("analytics", "v_admissions"), ("analytics", "v_patients")}


def test_accepts_select_and_adds_limit():
    sql = validate_sql("SELECT COUNT(*) AS n FROM analytics.v_admissions", VIEWS)
    assert "LIMIT 50" in sql


def test_unqualified_view_gets_its_schema():
    sql = validate_sql("SELECT COUNT(*) AS n FROM v_admissions", VIEWS)
    assert "analytics.v_admissions" in sql


def test_count_distinct_on_patient_key_is_allowed():
    validate_sql("SELECT COUNT(DISTINCT patient_key) AS n FROM analytics.v_admissions", VIEWS)


def test_large_limit_is_capped():
    sql = validate_sql("SELECT district FROM analytics.v_patients LIMIT 5000", VIEWS)
    assert "LIMIT 50" in sql and "5000" not in sql


def test_bound_filter_values_are_preserved_for_execution():
    sql = validate_sql(
        "SELECT gender FROM analytics.v_patients WHERE gender = :gender",
        VIEWS, {"gender"})
    assert "gender = :gender" in sql


@pytest.mark.parametrize("sql", [
    "SELECT gender FROM analytics.v_patients WHERE gender = 'F'",
    "SELECT district FROM analytics.v_patients WHERE district ILIKE '%Fianarantsoa%'",
])
def test_filter_values_must_be_bound(sql):
    with pytest.raises(ValueError, match="paramètres liés"):
        validate_sql(sql, VIEWS, set())


@pytest.mark.parametrize("bad", [
    "DROP TABLE analytics.v_patients",
    "UPDATE analytics.v_patients SET gender = 'x'",
    "SELECT 1; DROP TABLE x",
    "SELECT * FROM analytics.v_patients",
    "SELECT patient_key FROM analytics.v_patients",
    "SELECT name FROM public.patients",
    "SELECT COUNT(*) FROM public.patients",
    "SELECT pg_sleep(10)",
])
def test_rejects_dangerous_or_unapproved_sql(bad):
    with pytest.raises(ValueError):
        validate_sql(bad, VIEWS)
