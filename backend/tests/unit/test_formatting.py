from decimal import Decimal

from app.domain.formatting import fmt_value, format_result, grounded, numbers_in


def test_fmt_value():
    assert fmt_value(None) == "—"
    assert fmt_value(47597) == "47\u202f597"
    assert fmt_value(Decimal("3.50")) == "3.5"


def test_single_value_result():
    assert format_result(["total_patients"], [(47597,)]) == "Patients: 47\u202f597"
    assert format_result(["total_patients"], [(47597,)], "fr") == "Patients : 47\u202f597"


def test_table_and_empty_table():
    out = format_result(["district", "n"], [("A", 2), ("B", 10)])
    assert "District" in out and "B" in out
    assert "District" in format_result(["district", "n"], [])


def test_grounded_rejects_invented_numbers():
    assert numbers_in("1\u202f234 patients") == {"1234"}
    assert grounded("Il y a 12 visites.", "total : 12", "combien ?")
    assert not grounded("Il y a 99 visites.", "total : 12", "combien ?")


def test_french_table_headers_and_thin_space():
    out = format_result(["age_group", "total_admissions"], [("18-23", 47597)], "fr")
    assert "Tranche d'âge" in out
    assert "Admissions" in out
    assert "47\u202f597" in out


def test_english_and_malagasy_table_headers():
    columns = ["age_group", "total_patients"]

    assert "Age group" in format_result(columns, [("18-23", 10)], "en")
    assert "Sokajin-taona" in format_result(columns, [("18-23", 10)], "mg")
