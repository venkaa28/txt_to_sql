# Project Plan: CFG-Constrained NL→ClickHouse SQL App + Evals

## Goal
Build and deploy a small web app where a user types a natural-language question (e.g., “sum the total of all orders placed in the last 30 hours”), the system uses **GPT-5 with a Context-Free Grammar (CFG)** to generate **valid, schema-bound ClickHouse SQL**, executes it against ClickHouse (Tinybird or ClickHouse Cloud), and displays results. Include **3+ evals** that prove the CFG approach works.

---

## Success Criteria (Definition of Done)
- [ ] Deployed app URL with:
  - [ ] Input box for NL query
  - [ ] Display generated SQL
  - [ ] Display query results (table/JSON)
  - [ ] Clear error states (invalid query, empty results, rate limit, etc.)
- [ ] GPT-5 call uses **CFG** (not post-hoc regex) to constrain SQL output
- [ ] ClickHouse dataset ingested (1000+ rows) and queryable
- [ ] 3+ evals runnable via script and/or app endpoint
- [ ] Public GitHub repo with:
  - [ ] Clear README (setup, env vars, deploy)
  - [ ] Architecture overview
  - [ ] How to run evals

---

## Architecture Overview (Components + Responsibilities)
### A) Frontend (Web UI)
**Responsibilities**
- Text input for NL query
- “Run” button
- Render generated SQL + results
- Show error messages

**Non-goals**
- Auth, user accounts, query history

### B) Backend API (FastAPI/Express)
**Responsibilities**
- Accept NL query
- Build prompt + CFG
- Call GPT-5 with CFG constraint
- Validate SQL (defense-in-depth)
- Execute SQL in ClickHouse
- Return structured response

### C) Schema Registry (Single Source of Truth)
**Responsibilities**
- Store table schema (columns + types)
- Used to generate CFG terminals
- Used in validator + evals

### D) CFG (Star of the Project)
**Responsibilities**
- Constrain SQL to:
  - clickhouse sql dialect grammar (find official if possible, search internet if not, otherwise lets use the clickhouse docs to build it)
  - SELECT-only
  - Approved table(s)
  - Approved column names
  - Allowed aggregations and filters
  - Time-window patterns (e.g., last N hours/days)

### E) SQL Validator (Lightweight)
**Responsibilities**
- Should we use sqlglot for this as a lightweight sql parser?
- Parse/scan SQL
- Confirm table and columns ∈ schema
- Enforce read-only / no forbidden keywords

### F) Evals Runner
**Responsibilities**
- Run a set of NL queries through pipeline
- Assert properties (schema correctness, determinism, key intent checks)
- Print report + exit non-zero on failure

---

## Task Breakdown Plan

### 1) Choose Dataset + Ingest into ClickHouse
**Steps**
1. Pick a CSV dataset with 1000+ rows that maps well to analytical queries.
   - Prefer time-based fields like `created_at` so “last 30 hours” works.
   - Example domains: orders/ecommerce, trips, web events, taxi rides.
2. Create a table schema in ClickHouse:
   - Include at least: `created_at` (DateTime), numeric metric (`amount`), and identifiers.
3. Ingest CSV into ClickHouse (Tinybird or ClickHouse Cloud):
   - Use provider’s import UI or CLI
4. Verify with a simple query:
   - `SELECT count() FROM table;`
   - `SELECT max(created_at), min(created_at) FROM table;`

   - if imdb clickbench dataset is 1000+ rows, fits the above criteria, lets use it! https://github.com/ClickHouse/ClickBench?tab=readme-ov-file

**Deliverables**
- Table created + populated (1000+ rows)
- Connection string + read-only credentials (stored in env vars)

---

### 2) Define the Query Scope (Keep Grammar Small)
**Decision**
Support a minimal SQL subset that still answers common questions:
- Single table
- SELECT with:
  - aggregates: `count()`, `sum(col)`, `avg(col)`, `min(col)`, `max(col)`
  - optional `group by` on whitelisted dimensions
  - optional `order by` + `limit`
- WHERE filters limited to:
  - time window on a designated datetime column
  - equality filters on whitelisted dimensions

**Deliverables**
- A written “Supported Query Language” section for README

---

### 3) Implement Schema Registry
**Steps**
1. Create a schema file (JSON/YAML/TS/Python dict), e.g.:
   - `schema.json` with table name + columns + types
2. Load this schema in backend at startup
3. Expose helper functions:
   - `get_columns()`, `is_valid_column()`, etc.

**Deliverables**
- Schema registry module
- Unit test verifying schema loads

---

### 4) Build the CFG for ClickHouse SQL
**Steps**
1. Write an EBNF-style grammar for the supported SQL subset
2. Bake in:
   - fixed table name(s)
   - whitelisted column names as terminals
   - allowed aggregate functions
   - time-window clause pattern:
     - `created_at >= now() - INTERVAL <int> HOUR`
3. Add small optional extensions only if needed:
   - `AND <column> = '<value>'` for a limited set of categorical columns
4. Ensure grammar is strict enough that **invalid SQL cannot be produced**
5. Add a function that produces the CFG string from the schema registry

**Deliverables**
- `cfg.py` / `cfg.ts` module returning grammar string
- A couple of tests that ensure grammar contains all required columns and no others

---

### 5) NL → SQL Generation with GPT-5 + CFG
**Steps**
1. Implement `generate_sql(nl_query) -> sql_string`:
   - Build system prompt: “Generate ClickHouse SQL. Output SQL only.”
   - Provide schema context minimally (table + columns)
2. Call GPT-5 with:
   - `response_format` / CFG parameter from OpenAI cookbook example
3. Return the model output SQL (no explanation text)
4. Log the generated SQL in server logs for debugging (avoid logging secrets)

**Deliverables**
- `generate_sql()` function using GPT-5 with CFG
- Integration test with a sample NL query

---

### 6) Validate SQL (Defense-in-Depth)
**Steps**
1. Implement `validate_sql(sql) -> (ok, errors[])`:
   - Must start with `SELECT`
   - Must not contain forbidden keywords: `INSERT`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, etc.
   - Extract identifiers and verify columns in schema
   - Verify the FROM table is exactly allowed table
2. Fail fast if invalid

**Deliverables**
- Validator module + tests

---

### 7) Execute SQL Against ClickHouse + Return Results
**Steps**
1. Create ClickHouse client wrapper using env vars:
   - host, port, username, password, database
2. Execute SQL with safe settings:
   - set a max execution time (if available)
   - enforce row limit default (e.g., 100)
3. Return:
   - `sql`
   - `rows`
   - `columns`
   - `elapsed_ms`

**Deliverables**
- `run_query(sql)` function
- API endpoint `POST /query`

---

### 8) Build the Web App UI
**Steps**
1. Create a minimal page:
   - Textarea input
   - Run button
   - Display SQL in code block
   - Display results table
   - Display errors
2. Call backend `/query`
3. Add loading state

**Deliverables**
- Deployed UI (Vercel/Netlify) or served by backend

---

## Evals Plan (3+)

### Eval 1: Schema Correctness
**Goal**
Generated SQL references only valid table + columns.

**Method**
- Run N NL queries
- Validate SQL with validator
- Pass if 100% valid

**Output**
- pass rate, failing queries + SQL

---

### Eval 2: Determinism / Stability
**Goal**
For the same NL query, outputs remain valid across multiple samples.

**Method**
- For each of K queries, generate SQL M times (e.g., 10)
- Validate each SQL
- Pass if all M are valid (or >= threshold)

**Output**
- per-query validity %, example diffs

---

### Eval 3: Intent/Shape Checks (Lightweight)
**Goal**
SQL includes expected structural elements for certain prompts.

**Examples**
- “sum total” ⇒ contains `sum(`
- “count orders” ⇒ contains `count()`
- “last 30 hours” ⇒ contains `INTERVAL 30 HOUR` (or equivalent)
- “group by status” ⇒ contains `GROUP BY status`

**Method**
- For each test case, apply pattern assertions

**Output**
- pass/fail list with reasons

---

### (Optional) Eval 4: Execution Sanity
**Goal**
Generated SQL not only validates but executes successfully.

**Method**
- Execute SQL and assert:
  - no errors
  - returns within time limit

---

## Deployment Plan

### Recommended Minimal Deploy
- Frontend: Vercel (Next.js / static React)
- Backend: Railway / Fly.io / Render (FastAPI/Express)
- DB: Tinybird or ClickHouse Cloud

**Steps**
1. Add env var support:
   - `OPENAI_API_KEY`
   - `CLICKHOUSE_*`
2. Add `Dockerfile` for backend (optional but helps)
3. Deploy backend
4. Deploy frontend pointed to backend URL
5. Smoke test: run 3 sample queries end-to-end

**Deliverables**
- Deployed app URL
- README with deploy instructions

---

## Repo Structure Suggestion
/app
/frontend
/backend
schema.json
cfg.py
llm.py
validator.py
clickhouse.py
main.py
/evals
cases.json
run.py
README.md


---

## README Checklist
- [ ] What this app does
- [ ] Architecture diagram (ASCII)
- [ ] Supported query subset (explicit)
- [ ] How CFG is used (link to cookbook section)
- [ ] Local setup instructions
- [ ] Env vars
- [ ] How to run evals
- [ ] Deployment URLs

---

## Execution Order (Fast Path)
1. Ingest dataset + verify table
2. Implement schema registry
3. Implement CFG generation
4. Implement NL→SQL with GPT-5 + CFG
5. Implement SQL validator
6. Implement query execution endpoint
7. Build minimal UI
8. Add evals + report
9. Deploy + finalize README