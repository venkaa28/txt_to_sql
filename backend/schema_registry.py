"""
Schema Registry - Single source of truth for table schema.

Loads schema from JSON and provides helper functions for:
- Column validation
- CFG terminal generation
- Schema context for LLM prompts
"""

import json
from pathlib import Path
from typing import Optional

_schema: Optional[dict] = None


def load_schema(path: Optional[str] = None) -> dict:
    """Load schema from JSON file."""
    global _schema
    if _schema is not None and path is None:
        return _schema

    if path is None:
        path = Path(__file__).parent / "schema.json"
    else:
        path = Path(path)

    with open(path) as f:
        _schema = json.load(f)

    return _schema


def get_schema() -> dict:
    """Get the loaded schema, loading if necessary."""
    if _schema is None:
        load_schema()
    return _schema


def get_table_name() -> str:
    """Get the allowed table name."""
    return get_schema()["table"]


def get_columns() -> list[dict]:
    """Get all column definitions."""
    return get_schema()["columns"]


def get_column_names() -> list[str]:
    """Get list of all column names."""
    return [col["name"] for col in get_columns()]


def is_valid_column(name: str) -> bool:
    """Check if column name is valid."""
    return name.lower() in [col["name"].lower() for col in get_columns()]


def get_aggregatable_columns() -> list[str]:
    """Get columns that can be used in aggregate functions."""
    return [col["name"] for col in get_columns() if col.get("aggregatable")]


def get_groupable_columns() -> list[str]:
    """Get columns that can be used in GROUP BY."""
    return [col["name"] for col in get_columns() if col.get("groupable")]


def get_filterable_columns() -> list[str]:
    """Get columns that can be used in WHERE filters."""
    return [col["name"] for col in get_columns() if col.get("filterable")]


def get_datetime_column() -> str:
    """Get the primary datetime column for time-window queries."""
    return get_schema()["datetime_column"]


def get_supported_aggregates() -> list[str]:
    """Get list of allowed aggregate functions."""
    return get_schema()["supported_aggregates"]


def get_column_type(name: str) -> Optional[str]:
    """Get the ClickHouse type for a column."""
    for col in get_columns():
        if col["name"].lower() == name.lower():
            return col["type"]
    return None


def get_allowed_values(column: str) -> Optional[list[str]]:
    """Get allowed values for a categorical column."""
    for col in get_columns():
        if col["name"].lower() == column.lower():
            return col.get("allowed_values")
    return None


def get_schema_context_for_llm() -> str:
    """Generate schema context string for LLM prompt."""
    schema = get_schema()
    lines = [
        f"Table: {schema['table']}",
        "Columns:"
    ]

    for col in schema["columns"]:
        col_desc = f"  - {col['name']} ({col['type']}): {col['description']}"
        if col.get("allowed_values"):
            col_desc += f" [allowed: {', '.join(col['allowed_values'])}]"
        lines.append(col_desc)

    lines.extend([
        f"\nDatetime column for time filters: {schema['datetime_column']}",
        f"Supported aggregates: {', '.join(schema['supported_aggregates'])}",
        f"Max result limit: {schema['max_limit']}"
    ])

    return "\n".join(lines)


def get_default_limit() -> int:
    """Get default row limit for queries."""
    return get_schema().get("default_limit", 100)


def get_max_limit() -> int:
    """Get maximum row limit for queries."""
    return get_schema().get("max_limit", 1000)
