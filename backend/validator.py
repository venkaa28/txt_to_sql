"""
SQL Validator - Defense-in-depth validation for generated SQL.

Uses sqlglot to parse and validate SQL queries against the schema.
Ensures generated SQL is safe even if CFG constraint is bypassed.
"""

import re
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from schema_registry import get_table_name, get_column_names

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "ATTACH", "DETACH",
    "RENAME", "OPTIMIZE", "KILL", "SYSTEM", "ADMIN",
}

_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)


def _strip_comments(sql: str) -> str:
    return _COMMENT_RE.sub(" ", sql)


def validate_sql(sql: str, schema_name: str = "default") -> tuple[bool, list[str]]:
    """
    Validate SQL query against schema and security rules.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    cleaned_sql = _strip_comments(sql)
    sql_upper = cleaned_sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\\b{keyword}\\b", sql_upper):
            errors.append(f"Forbidden keyword: {keyword}")

    if errors:
        return False, errors

    try:
        statements = sqlglot.parse(cleaned_sql, dialect="clickhouse")
        if len(statements) != 1:
            errors.append("Only single SELECT statements are allowed")
            return False, errors
        parsed = statements[0]
    except ParseError as e:
        errors.append(f"SQL parse error: {e}")
        return False, errors

    if not isinstance(parsed, exp.Select):
        errors.append("Only SELECT statements are allowed")
        return False, errors

    allowed_table = get_table_name(schema_name).lower()
    for table in parsed.find_all(exp.Table):
        if table.name.lower() != allowed_table:
            errors.append(f"Invalid table: {table.name}")

    valid_columns = {col.lower() for col in get_column_names(schema_name)}
    valid_columns.add("*")
    for column in parsed.find_all(exp.Column):
        if column.name.lower() not in valid_columns:
            errors.append(f"Invalid column: {column.name}")

    return len(errors) == 0, errors


def enforce_limit(
    sql: str,
    default_limit: int,
    max_limit: int
) -> tuple[bool, str, list[str]]:
    """
    Ensure a LIMIT exists and does not exceed max_limit.
    Returns (ok, sql, errors).
    """
    errors = []
    cleaned_sql = _strip_comments(sql).strip().rstrip(";")
    limit_match = re.search(r"\blimit\s+(\d+)\b", cleaned_sql, flags=re.IGNORECASE)

    if not limit_match:
        return True, f"{cleaned_sql} LIMIT {default_limit}", []

    limit_value = int(limit_match.group(1))
    if limit_value > max_limit:
        updated_sql = re.sub(
            r"\blimit\s+\d+\b",
            f"LIMIT {max_limit}",
            cleaned_sql,
            flags=re.IGNORECASE
        )
        return True, updated_sql, []

    return True, cleaned_sql, []
