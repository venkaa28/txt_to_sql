"""
SQL Validator - Defense-in-depth validation for generated SQL.

Uses sqlglot to parse and validate SQL queries against the schema.
Ensures generated SQL is safe even if CFG constraint is bypassed.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from schema_registry import get_table_name, get_column_names

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "ATTACH", "DETACH",
    "RENAME", "OPTIMIZE", "KILL", "SYSTEM", "ADMIN",
}


def validate_sql(sql: str) -> tuple[bool, list[str]]:
    """
    Validate SQL query against schema and security rules.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper.split():
            errors.append(f"Forbidden keyword: {keyword}")

    if errors:
        return False, errors

    try:
        parsed = sqlglot.parse_one(sql, dialect="clickhouse")
    except ParseError as e:
        errors.append(f"SQL parse error: {e}")
        return False, errors

    if not isinstance(parsed, exp.Select):
        errors.append("Only SELECT statements are allowed")
        return False, errors

    allowed_table = get_table_name().lower()
    for table in parsed.find_all(exp.Table):
        if table.name.lower() != allowed_table:
            errors.append(f"Invalid table: {table.name}")

    valid_columns = {col.lower() for col in get_column_names()}
    valid_columns.add("*")
    for column in parsed.find_all(exp.Column):
        if column.name.lower() not in valid_columns:
            errors.append(f"Invalid column: {column.name}")

    return len(errors) == 0, errors
