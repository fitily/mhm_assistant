import re

from app.core.dictionary import approved_views
from app.domain.sql.examples import EXAMPLES
from app.domain.sql.validator import validate_sql


def test_few_shot_examples_are_validated_against_approved_views():
    for _, sql, params in EXAMPLES:
        params = set(re.findall(r"(?<!:):([A-Za-z_]\w*)", sql))
        checked = validate_sql(sql, set(approved_views()), params)
        assert "analytics." in checked
