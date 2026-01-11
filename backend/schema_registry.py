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

DEFAULT_SCHEMA = "default"
_schema_cache: dict[str, dict] = {}


def _resolve_schema_path(name: str, path: Optional[str]) -> Path:
    if path:
        return Path(path)
    if name == DEFAULT_SCHEMA:
        return Path(__file__).parent / "schema.json"
    return Path(__file__).parent / "schemas" / f"{name}.json"


def load_schema(name: str = DEFAULT_SCHEMA, path: Optional[str] = None) -> dict:
    """Load schema from JSON file."""
    if name in _schema_cache and path is None:
        return _schema_cache[name]

    schema_path = _resolve_schema_path(name, path)
    with open(schema_path) as f:
        _schema_cache[name] = json.load(f)

    return _schema_cache[name]


def get_schema(name: str = DEFAULT_SCHEMA) -> dict:
    """Get the loaded schema, loading if necessary."""
    if name not in _schema_cache:
        load_schema(name=name)
    return _schema_cache[name]


def get_table_name(name: str = DEFAULT_SCHEMA) -> str:
    """Get the allowed table name."""
    return get_schema(name)["table"]


def get_columns(name: str = DEFAULT_SCHEMA) -> list[dict]:
    """Get all column definitions."""
    return get_schema(name)["columns"]


def get_column_names(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get list of all column names."""
    return [col["name"] for col in get_columns(name)]


def is_valid_column(name: str, schema_name: str = DEFAULT_SCHEMA) -> bool:
    """Check if column name is valid."""
    return name.lower() in [col["name"].lower() for col in get_columns(schema_name)]


def get_aggregatable_columns(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get columns that can be used in aggregate functions."""
    return [col["name"] for col in get_columns(name) if col.get("aggregatable")]


def get_groupable_columns(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get columns that can be used in GROUP BY."""
    return [col["name"] for col in get_columns(name) if col.get("groupable")]


def get_filterable_columns(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get columns that can be used in WHERE filters."""
    return [col["name"] for col in get_columns(name) if col.get("filterable")]


def get_datetime_column(name: str = DEFAULT_SCHEMA) -> str:
    """Get the primary datetime column for time-window queries."""
    return get_schema(name)["datetime_column"]


def get_datetime_columns(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get columns that are datetime-like."""
    return [col["name"] for col in get_columns(name) if col.get("is_datetime")]


def get_supported_aggregates(name: str = DEFAULT_SCHEMA) -> list[str]:
    """Get list of allowed aggregate functions."""
    return get_schema(name)["supported_aggregates"]


def get_column_type(name: str, schema_name: str = DEFAULT_SCHEMA) -> Optional[str]:
    """Get the ClickHouse type for a column."""
    for col in get_columns(schema_name):
        if col["name"].lower() == name.lower():
            return col["type"]
    return None


def get_allowed_values(column: str, schema_name: str = DEFAULT_SCHEMA) -> Optional[list[str]]:
    """Get allowed values for a categorical column."""
    for col in get_columns(schema_name):
        if col["name"].lower() == column.lower():
            return col.get("allowed_values")
    return None


def get_schema_context_for_llm(name: str = DEFAULT_SCHEMA) -> str:
    """Generate schema context string for LLM prompt."""
    schema = get_schema(name)
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


def get_default_limit(name: str = DEFAULT_SCHEMA) -> int:
    """Get default row limit for queries."""
    return get_schema(name).get("default_limit", 100)


def get_max_limit(name: str = DEFAULT_SCHEMA) -> int:
    """Get maximum row limit for queries."""
    return get_schema(name).get("max_limit", 1000)
