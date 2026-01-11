# NL → ClickHouse SQL with CFG

Convert natural language questions to valid ClickHouse SQL using GPT-5's Context-Free Grammar (CFG) constraint.

## Live Demo

- **Frontend**: https://txt-to-sql-sandy.vercel.app
- **Backend API**: https://txttosql-production.up.railway.app
- **API Health**: https://txttosql-production.up.railway.app/health

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌──────────┐
│   Frontend  │────▶│           Backend (FastAPI)         │────▶│ Tinybird │
│   (Svelte)  │     │                                     │     │ClickHouse│
└─────────────┘     │  ┌─────────┐  ┌─────────┐  ┌─────┐  │     └──────────┘
                    │  │ GPT-5 + │─▶│Validator│─▶│Query│  │
                    │  │   CFG   │  │(sqlglot)│  │ Exec│  │
                    │  └─────────┘  └─────────┘  └─────┘  │
                    └─────────────────────────────────────┘
```

## How CFG Works

Instead of generating arbitrary SQL and hoping it's valid, we use OpenAI GPT-5's **Context-Free Grammar** feature to constrain output at generation time:

1. **Grammar Definition**: A Lark grammar defines valid SQL syntax for our schema
2. **Tool Constraint**: GPT-5 uses the grammar as a tool format constraint
3. **Guaranteed Valid Syntax**: The model can only output strings that match the grammar

This is more reliable than post-hoc regex validation because invalid SQL _cannot be generated_.

Reference: [OpenAI Cookbook - GPT-5 CFG](https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools)

## Supported Query Subset

The CFG allows:

- `SELECT` statements only (no INSERT, UPDATE, DELETE)
- Single table: `trips`
- Aggregates: `count()`, `sum()`, `avg()`, `min()`, `max()`
- `WHERE` filters: time windows, equality on categorical columns, duration filters via `dateDiff(...)`
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
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Rate limiting (optional)
RATE_LIMIT_REQUESTS=10     # Max requests per window (default: 10)
RATE_LIMIT_WINDOW=60       # Time window in seconds (default: 60)
```

**Note**: Rate limiting is automatically disabled for localhost to allow evals to run.

## API

### POST /query

Convert natural language to SQL and execute.

**Request:**

```json
{
  "query": "How many taxi trips in the last 24 hours?",
  "schema": "default"
}
```

**Response:**

```json
{
  "success": true,
  "sql": "SELECT count() FROM trips WHERE tpep_pickup_datetime >= now() - INTERVAL 24 HOUR",
  "data": [{ "count()": 12345 }],
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

Evals call the OpenAI API via the backend LLM module, so you need your own `OPENAI_API_KEY`. The runner will load `backend/.env` automatically if it exists (and `python-dotenv` is installed).

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

Uses Tinybird's public NYC Yellow Taxi sample data with columns:

- `tpep_pickup_datetime`, `tpep_dropoff_datetime` (DateTime)
- `passenger_count` (Int64)
- `trip_distance` (Float64)
- `fare_amount`, `tip_amount`, `total_amount` (Float64)
- `payment_type` (Int64: 1=Credit, 2=Cash, 3=No Charge, 4=Dispute)
- `PULocationID`, `DOLocationID` (Int32)

### Ingest into Tinybird

1. Create a Tinybird data source from the public sample (over 1k rows):

```bash
tb --cloud datasource create --url https://tbrd.co/taxi_data.parquet --name trips
```

If you don't use the CLI, create a new Data Source in Tinybird Cloud and import the URL above with the name `trips`.

2. Verify in Tinybird SQL console:

```sql
SELECT count() FROM trips;
```

## License

MIT
