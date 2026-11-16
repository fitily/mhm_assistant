import datetime as dt

from app.domain.periods import normalize_question, parse_period

TODAY = dt.date(2026, 11, 11)


def test_month_and_year():
    p = parse_period("Combien de visites en mars 2026 ?", TODAY)
    assert (p.start, p.end) == (dt.date(2026, 3, 1), dt.date(2026, 4, 1))


def test_typo_in_month_is_fixed():
    assert normalize_question("visites en javier 2026") == "visites en janvier 2026"
    assert parse_period("visites en javier 2026", TODAY).start == dt.date(2026, 1, 1)


def test_december_rolls_to_next_year():
    assert parse_period("décembre 2025", TODAY).end == dt.date(2026, 1, 1)


def test_last_month_and_this_month():
    assert parse_period("le mois dernier", TODAY).start == dt.date(2026, 10, 1)
    assert parse_period("ce mois", TODAY).end == dt.date(2026, 12, 1)


def test_whole_year():
    p = parse_period("admissions en 2025", TODAY)
    assert (p.start, p.end) == (dt.date(2025, 1, 1), dt.date(2026, 1, 1))


def test_no_period():
    assert parse_period("combien de patients ?", TODAY) is None
