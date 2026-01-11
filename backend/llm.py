"""
LLM Module - NL to SQL generation using OpenAI GPT-5 with CFG.

Uses OpenAI's Responses API with Context-Free Grammar tool
to generate valid, schema-bound ClickHouse SQL.

Reference: https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools
"""

import os
import logging
from typing import Optional, Any
from openai import OpenAI

from schema_registry import get_schema_context_for_llm
from cfg import generate_clickhouse_grammar

logger = logging.getLogger(__name__)

_client = None

# Cache grammar and tool per schema name
_cached_grammar: dict[str, str] = {}
_cached_tool: dict[str, dict] = {}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _get_cfg_tool(schema_name: str = "default") -> dict:
    """Get CFG tool definition, cached per schema name."""
    if schema_name not in _cached_tool:
        _cached_grammar[schema_name] = generate_clickhouse_grammar(schema_name)
        _cached_tool[schema_name] = {
            "type": "custom",
            "name": "clickhouse_query",
            "description": (
                "Executes read-only ClickHouse SQL queries against the configured dataset. "
                "Limited to SELECT statements with aggregations, WHERE filters, GROUP BY, ORDER BY, and LIMIT. "
                "YOU MUST REASON HEAVILY ABOUT THE QUERY AND MAKE SURE IT OBEYS THE GRAMMAR."
            ),
            "format": {
                "type": "grammar",
                "syntax": "lark",
                "definition": _cached_grammar[schema_name]
            }
        }
    return _cached_tool[schema_name]


SYSTEM_PROMPT = """You are a SQL assistant that converts natural language questions into ClickHouse SQL queries.

Rules:
1. Generate ONLY valid ClickHouse SQL - no explanations, no markdown, just SQL
2. Use only the columns and table provided in the schema
3. For time-based questions like "last N hours/days", use: column >= now() - INTERVAL N UNIT
4. For duration questions, use dateDiff('hour'|'day'|..., start_datetime, end_datetime) comparisons
5. Use appropriate aggregate functions: count(), sum(), avg(), min(), max()
6. Include GROUP BY when using aggregates with non-aggregated columns
7. Add reasonable LIMIT (default 100) to prevent huge result sets
8. Use ORDER BY for meaningful result ordering

Schema context:
{schema_context}
"""


def generate_sql(natural_language_query: str, schema_name: str = "default") -> dict:
    """
    Convert natural language to ClickHouse SQL using GPT-5 with CFG constraint.

    Args:
        natural_language_query: User's question in natural language

    Returns:
        dict with keys:
            - sql: Generated SQL string
            - success: bool
            - error: Error message if failed
    """
    try:
        client = _get_client()
        schema_context = get_schema_context_for_llm(schema_name)
        system_prompt = SYSTEM_PROMPT.format(schema_context=schema_context)

        prompt = f"{system_prompt}\n\nUser question: {natural_language_query}\n\nGenerate the SQL query:"

        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            tools=[_get_cfg_tool(schema_name)],
            tool_choice={"type": "custom", "name": "clickhouse_query"},
        )

        # Extract SQL from response (tool output or direct text)
        sql = _extract_sql_from_response(response)

        if not sql:
            _log_response_summary(response)
            return {"sql": None, "success": False, "error": "No SQL generated in response"}

        sql = sql.strip().rstrip(';')
        logger.info(f"Generated SQL: {sql}")

        return {"sql": sql, "success": True, "error": None}

    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        return {"sql": None, "success": False, "error": str(e)}


def _extract_sql_from_response(response) -> Optional[str]:
    """Best-effort extraction across response formats."""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    outputs = getattr(response, "output", []) or []
    for output in outputs:
        otype = getattr(output, "type", None)
        content = getattr(output, "content", None)

        if otype == "custom_tool_use":
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "".join(parts).strip()

        if otype == "output_text" and content:
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "".join(parts).strip()

    # Last-resort: search any string in the raw response dump
    response_dump = None
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        response_dump = model_dump()
    elif isinstance(response, dict):
        response_dump = response

    sql = _find_sql_in_value(response_dump)
    if sql:
        return sql

    return None


def _find_sql_in_value(value: Any) -> Optional[str]:
    """Recursively search for a SQL-looking string in a nested structure."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.lower().startswith("select "):
            return candidate
        return None
    if isinstance(value, list):
        for item in value:
            found = _find_sql_in_value(item)
            if found:
                return found
        return None
    if isinstance(value, dict):
        for item in value.values():
            found = _find_sql_in_value(item)
            if found:
                return found
        return None
    return None


def _log_response_summary(response) -> None:
    """Log a compact summary of response output types for debugging."""
    outputs = getattr(response, "output", []) or []
    types = []
    for output in outputs:
        otype = getattr(output, "type", None)
        if otype:
            types.append(otype)
        elif isinstance(output, dict) and "type" in output:
            types.append(output["type"])
    if types:
        logger.warning("No SQL found. Response output types: %s", types)
    else:
        logger.warning("No SQL found. Response output was empty or unrecognized.")


if __name__ == "__main__":
    import sys

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    test_queries = [
        "How many taxi trips are in the database?",
        "What is the average fare amount?",
        "Show me the total revenue in the last 24 hours",
        "Count trips by payment type",
    ]

    print("Testing NL to SQL generation:")
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = generate_sql(query)
        print(f"SQL: {result['sql']}" if result["success"] else f"Error: {result['error']}")
