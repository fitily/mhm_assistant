import datetime as dt

import pytest

from app.core.errors import OutOfRange
from app.domain.models import Period
from app.domain.sql import executor


def test_fully_covered_period_is_not_marked_out_of_range(monkeypatch):
    monkeypatch.setattr(executor, "data_range", lambda: (
        dt.date(2022, 6, 28), dt.date(2026, 9, 16)))

    notes = executor.check_range(
        Period(dt.date(2026, 7, 1), dt.date(2026, 8, 1), "juillet 2026"),
        dt.date(2026, 11, 12))

    assert notes == []


def test_period_after_data_cutoff_is_rejected(monkeypatch):
    monkeypatch.setattr(executor, "data_range", lambda: (
        dt.date(2022, 6, 28), dt.date(2026, 9, 16)))

    with pytest.raises(OutOfRange):
        executor.check_range(
            Period(dt.date(2026, 10, 1), dt.date(2026, 11, 1), "octobre 2026"),
            dt.date(2026, 11, 12))
