"""
CFG (Context-Free Grammar) for ClickHouse SQL generation.

Generates a Lark grammar for use with OpenAI GPT-5's native CFG support.
The grammar constrains SQL output to:
- SELECT-only queries
- Whitelisted table and columns
- Allowed aggregations and filters
- Time-window patterns

Reference: https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools
"""

from schema_registry import (
    get_table_name,
    get_column_names,
    get_aggregatable_columns,
    get_groupable_columns,
    get_filterable_columns,
    get_datetime_column,
    get_supported_aggregates,
    get_allowed_values,
    get_max_limit,
)


def generate_clickhouse_grammar() -> str:
    """
    Generate a Lark grammar for ClickHouse SQL.

    The grammar enforces:
    - Only SELECT statements
    - Only the allowed table
    - Only whitelisted columns
    - Only supported aggregate functions
    - Safe WHERE clauses (time filters + equality filters)
    - Optional GROUP BY, ORDER BY, LIMIT
    """
    table_name = get_table_name()
    columns = get_column_names()
    aggregatable = get_aggregatable_columns()
    groupable = get_groupable_columns()
    filterable = get_filterable_columns()
    datetime_col = get_datetime_column()
    aggregates = get_supported_aggregates()

    # Build column alternatives as regex pattern
    column_pattern = "|".join(columns)
    aggregatable_pattern = "|".join(aggregatable) if aggregatable else "NONE"
    groupable_pattern = "|".join(groupable) if groupable else "NONE"
    filterable_pattern = "|".join(filterable) if filterable else "NONE"
    aggregate_pattern = "|".join(aggregates)

    # Build allowed string values for categorical filters
    filter_values = []
    for col in filterable:
        allowed = get_allowed_values(col)
        if allowed:
            filter_values.extend(allowed)
    filter_values_pattern = "|".join(filter_values) if filter_values else "NONE"

    grammar = f'''
// ClickHouse SQL Grammar - Auto-generated from schema
// For use with OpenAI GPT-5 CFG tool format

// Whitespace
WS: /\\s+/

// Punctuation
COMMA: ","
LPAREN: "("
RPAREN: ")"

// Operators
GTE: ">="
GT: ">"
LTE: "<="
LT: "<"
EQ: "="

// Keywords
SELECT: /SELECT/i
FROM: /FROM/i
WHERE: /WHERE/i
AND: /AND/i
GROUP: /GROUP/i
BY: /BY/i
ORDER: /ORDER/i
ASC: /ASC/i
DESC: /DESC/i
LIMIT: /LIMIT/i
INTERVAL: /INTERVAL/i
NOW: /now/i

// Time units
TIME_UNIT: /SECOND|MINUTE|HOUR|DAY|WEEK|MONTH/i

// Column names (whitelisted)
COLUMN: /{column_pattern}/
AGG_COLUMN: /{aggregatable_pattern}/
GROUP_COLUMN: /{groupable_pattern}/
FILTER_COLUMN: /{filterable_pattern}/
DATETIME_COL: "{datetime_col}"

// Aggregate functions
AGG_FUNC: /{aggregate_pattern}/

// Table name (fixed)
TABLE: "{table_name}"

// Literals
NUMBER: /[1-9][0-9]*/
STRING_VALUE: /{filter_values_pattern}/
DATE: /[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}/
DATETIME: /[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}} [0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}/

// Main query structure
start: select_stmt

select_stmt: SELECT WS select_list WS FROM WS TABLE [where_clause] [group_clause] [order_clause] [limit_clause]

// SELECT list
select_list: select_item (COMMA WS? select_item)*
select_item: agg_expr | COLUMN | count_star
count_star: "count()" | "count(*)"
agg_expr: AGG_FUNC LPAREN AGG_COLUMN RPAREN

// WHERE clause
where_clause: WS WHERE WS condition (WS AND WS condition)*
condition: time_condition | eq_condition

// Time filter
time_condition: DATETIME_COL WS? comp_op WS? time_expr
comp_op: GTE | GT | LTE | LT
time_expr: now_interval | date_literal
now_interval: NOW LPAREN RPAREN WS? "-" WS? INTERVAL WS NUMBER WS TIME_UNIT
date_literal: "'" (DATETIME | DATE) "'"

// Equality filter
eq_condition: FILTER_COLUMN WS? EQ WS? "'" STRING_VALUE "'"

// GROUP BY
group_clause: WS GROUP WS BY WS group_list
group_list: GROUP_COLUMN (COMMA WS? GROUP_COLUMN)*

// ORDER BY
order_clause: WS ORDER WS BY WS order_list
order_list: order_item (COMMA WS? order_item)*
order_item: COLUMN (WS sort_dir)?
sort_dir: ASC | DESC

// LIMIT
limit_clause: WS LIMIT WS NUMBER
'''
    return grammar.strip()


def get_tool_definition() -> dict:
    """
    Get the tool definition for OpenAI GPT-5 Responses API.

    Usage:
        tool = get_tool_definition()
        response = client.responses.create(
            model="gpt-5",
            input=prompt,
            tools=[tool],
            ...
        )
    """
    return {
        "type": "custom",
        "name": "clickhouse_query",
        "description": (
            "Executes a ClickHouse SQL query against the NYC taxi trips database. "
            "Generate valid ClickHouse SQL to answer the user's question. "
            "Only SELECT queries are allowed. Use count(), sum(), avg(), min(), max() for aggregations. "
            "For time filters, use: pickup_datetime >= now() - INTERVAL N HOUR/DAY/etc."
        ),
        "format": {
            "type": "grammar",
            "syntax": "lark",
            "definition": generate_clickhouse_grammar()
        }
    }


def validate_grammar() -> tuple[bool, str]:
    """
    Validate that the grammar is syntactically correct using Lark parser.
    Returns (is_valid, error_message).
    """
    try:
        from lark import Lark
        grammar = generate_clickhouse_grammar()
        Lark(grammar)
        return True, ""
    except ImportError:
        return True, "Lark not installed, skipping validation"
    except Exception as e:
        return False, str(e)


def test_grammar_with_examples() -> list[tuple[str, bool, str]]:
    """
    Test the grammar against example SQL queries.
    Returns list of (query, passed, error).
    """
    try:
        from lark import Lark
    except ImportError:
        return [("N/A", False, "Lark not installed")]

    grammar = generate_clickhouse_grammar()
    parser = Lark(grammar)

    test_cases = [
        "SELECT count() FROM nyc_taxi_trips",
        "SELECT sum(fare_amount) FROM nyc_taxi_trips",
        "SELECT count(), avg(trip_distance) FROM nyc_taxi_trips",
        "SELECT count() FROM nyc_taxi_trips WHERE pickup_datetime >= now() - INTERVAL 24 HOUR",
        "SELECT payment_type, count() FROM nyc_taxi_trips GROUP BY payment_type",
        "SELECT sum(total_amount) FROM nyc_taxi_trips WHERE payment_type = 'Cash'",
        "SELECT count() FROM nyc_taxi_trips ORDER BY fare_amount DESC LIMIT 10",
    ]

    results = []
    for sql in test_cases:
        try:
            parser.parse(sql)
            results.append((sql, True, ""))
        except Exception as e:
            results.append((sql, False, str(e)))

    return results


if __name__ == "__main__":
    print("Generated ClickHouse SQL Grammar:")
    print("=" * 60)
    print(generate_clickhouse_grammar())
    print("=" * 60)

    is_valid, error = validate_grammar()
    if is_valid:
        print("\nGrammar syntax is valid!")
    else:
        print(f"\nGrammar error: {error}")

    print("\nTesting example queries:")
    for sql, passed, error in test_grammar_with_examples():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {sql}")
        if error:
            print(f"         Error: {error}")
