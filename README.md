# NL → ClickHouse SQL with CFG

Convert natural language questions to valid ClickHouse SQL using GPT-5's Context-Free Grammar (CFG) constraint.

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌──────────┐
│   Frontend  │────▶│           Backend (FastAPI)         │────▶│ Tinybird │
│   (Svelte)  │     │                                     │     │ClickHouse│
└─────────────┘     │  ┌─────────┐  ┌─────────┐  ┌─────┐ │     └──────────┘
                    │  │ GPT-5 + │─▶│Validator│─▶│Query│ │
                    │  │   CFG   │  │(sqlglot)│  │ Exec│ │
                    │  └─────────┘  └─────────┘  └─────┘ │
                    └─────────────────────────────────────┘
```

## How CFG Works

Instead of generating arbitrary SQL and hoping it's valid, we use OpenAI GPT-5's **Context-Free Grammar** feature to constrain output at generation time:

1. **Grammar Definition**: A Lark grammar defines valid SQL syntax for our schema
2. **Tool Constraint**: GPT-5 uses the grammar as a tool format constraint
3. **Guaranteed Valid Syntax**: The model can only output strings that match the grammar

This is more reliable than post-hoc regex validation because invalid SQL *cannot be generated*.

Reference: [OpenAI Cookbook - GPT-5 CFG](https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools)

## Supported Query Subset

The CFG allows:
- `SELECT` statements only (no INSERT, UPDATE, DELETE)
- Single table: `nyc_taxi_trips`
- Aggregates: `count()`, `sum()`, `avg()`, `min()`, `max()`
- `WHERE` filters: time windows, equality on categorical columns
- `GROUP BY` on allowed dimensions
- `ORDER BY` + `LIMIT`

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- OpenAI API key (GPT-5 access)
- Tinybird account with NYC taxi data

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy env file and fill in values
cp .env.example .env

# Run server
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

```
OPENAI_API_KEY=sk-...      # OpenAI API key
TINYBIRD_TOKEN=p.eyJ...    # Tinybird auth token
TINYBIRD_HOST=https://api.tinybird.co
```

## API

### POST /query

Convert natural language to SQL and execute.

**Request:**
```json
{
  "query": "How many taxi trips in the last 24 hours?"
}
```

**Response:**
```json
{
  "success": true,
  "sql": "SELECT count() FROM nyc_taxi_trips WHERE pickup_datetime >= now() - INTERVAL 24 HOUR",
  "data": [{"count()": 12345}],
  "columns": ["count()"],
  "row_count": 1,
  "elapsed_ms": 45.2
}
```

## Evals

Run the evaluation suite:

```bash
cd evals
python run.py              # Run all evals
python run.py --eval schema    # Schema correctness only
python run.py --eval intent    # Intent checks only
python run.py --eval determinism  # Determinism only
```

### Eval 1: Schema Correctness
Verifies generated SQL only references valid tables and columns.

### Eval 2: Intent Checks
Verifies SQL contains expected patterns (e.g., "total fare" → `sum(fare_amount)`).

### Eval 3: Determinism
Verifies same query produces valid SQL across multiple samples.

## Project Structure

```
├── backend/
│   ├── main.py           # FastAPI app
│   ├── llm.py            # GPT-5 + CFG integration
│   ├── cfg.py            # Grammar generation
│   ├── validator.py      # SQL validation (sqlglot)
│   ├── tinybird.py       # Tinybird client
│   ├── schema_registry.py
│   ├── schema.json       # Table schema
│   └── requirements.txt
├── frontend/             # Svelte app
├── evals/
│   ├── cases.json        # Test cases
│   └── run.py            # Eval runner
└── README.md
```

## Dataset

Uses NYC Yellow Taxi trip data with columns:
- `pickup_datetime`, `dropoff_datetime` (DateTime)
- `passenger_count` (UInt8)
- `trip_distance` (Float64)
- `fare_amount`, `tip_amount`, `total_amount` (Float64)
- `payment_type` (String: Cash, Credit, No Charge, Dispute)
- `pickup_location_id`, `dropoff_location_id` (UInt16)

## License

MIT
