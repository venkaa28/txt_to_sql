import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schema_registry import get_default_limit, get_max_limit
from validator import validate_sql, enforce_limit


def test_forbidden_keyword_with_punctuation_rejected():
    ok, errors = validate_sql("SELECT count() FROM trips; DROP TABLE trips")
    assert not ok
    assert any("Forbidden keyword" in error or "single SELECT" in error for error in errors)


def test_default_limit_added():
    ok, sql, errors = enforce_limit(
        "SELECT count() FROM trips",
        default_limit=get_default_limit(),
        max_limit=get_max_limit()
    )
    assert ok
    assert not errors
    assert "limit" in sql.lower()
    assert f"limit {get_default_limit()}" in sql.lower()


def test_limit_capped_to_max():
    max_limit = get_max_limit()
    ok, sql, errors = enforce_limit(
        f"SELECT count() FROM trips LIMIT {max_limit + 500}",
        default_limit=get_default_limit(),
        max_limit=max_limit
    )
    assert ok
    assert not errors
    assert f"limit {max_limit}" in sql.lower()
