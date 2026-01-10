"""
LLM Module - NL to SQL generation using OpenAI GPT-5 with CFG.

Uses OpenAI's Responses API with Context-Free Grammar tool
to generate valid, schema-bound ClickHouse SQL.

Reference: https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools
"""

import os
import logging
from openai import OpenAI

from schema_registry import get_schema_context_for_llm
from cfg import generate_clickhouse_grammar

logger = logging.getLogger(__name__)

_client = None

# Cache grammar and tool at module level (generated once on first import)
_cached_grammar = None
_cached_tool = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _get_cfg_tool() -> dict:
    """Get CFG tool definition, cached at module level."""
    global _cached_grammar, _cached_tool
    if _cached_tool is None:
        _cached_grammar = generate_clickhouse_grammar()
        _cached_tool = {
            "type": "custom",
            "name": "clickhouse_query",
            "description": (
                "Executes read-only ClickHouse SQL queries against the NYC taxi trips database. "
                "Limited to SELECT statements with aggregations, WHERE filters, GROUP BY, ORDER BY, and LIMIT. "
                "YOU MUST REASON HEAVILY ABOUT THE QUERY AND MAKE SURE IT OBEYS THE GRAMMAR."
            ),
            "format": {
                "type": "grammar",
                "syntax": "lark",
                "definition": _cached_grammar
            }
        }
    return _cached_tool


SYSTEM_PROMPT = """You are a SQL assistant that converts natural language questions into ClickHouse SQL queries.

Rules:
1. Generate ONLY valid ClickHouse SQL - no explanations, no markdown, just SQL
2. Use only the columns and table provided in the schema
3. For time-based questions like "last N hours/days", use: column >= now() - INTERVAL N UNIT
4. Use appropriate aggregate functions: count(), sum(), avg(), min(), max()
5. Include GROUP BY when using aggregates with non-aggregated columns
6. Add reasonable LIMIT (default 100) to prevent huge result sets
7. Use ORDER BY for meaningful result ordering

Schema context:
{schema_context}
"""


def generate_sql(natural_language_query: str) -> dict:
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
        schema_context = get_schema_context_for_llm()
        system_prompt = SYSTEM_PROMPT.format(schema_context=schema_context)

        prompt = f"{system_prompt}\n\nUser question: {natural_language_query}\n\nGenerate the SQL query:"

        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            tools=[_get_cfg_tool()],
        )

        # Extract SQL from tool call output
        sql = None
        for output in response.output:
            if hasattr(output, 'type') and output.type == "custom_tool_use":
                sql = output.content
                break

        if not sql:
            return {"sql": None, "success": False, "error": "No SQL generated in response"}

        sql = sql.strip().rstrip(';')
        logger.info(f"Generated SQL: {sql}")

        return {"sql": sql, "success": True, "error": None}

    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        return {"sql": None, "success": False, "error": str(e)}


if __name__ == "__main__":
    # Test the module
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
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = generate_sql(query, use_cfg=False)  # Use non-CFG for initial testing
        if result["success"]:
            print(f"SQL: {result['sql']}")
        else:
            print(f"Error: {result['error']}")
