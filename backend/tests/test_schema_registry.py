import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schema_registry import get_table_name, get_column_names, get_datetime_column


def test_schema_registry_basics():
    assert get_table_name() == "trips"
    columns = get_column_names()
    assert "tpep_pickup_datetime" in columns
    assert get_datetime_column() in columns
