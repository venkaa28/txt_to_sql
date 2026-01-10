# Frontend Plan: Svelte + Vite

## Overview
Build a simple web UI for the NL→SQL application using Svelte + Vite.

## Tech Stack
- **Framework**: Svelte (not SvelteKit - keep it simple)
- **Build**: Vite
- **Styling**: Vanilla CSS or Tailwind (your choice)
- **HTTP**: Native fetch API

## Features

### 1. Input Section
- Textarea for natural language query
- "Run Query" button
- Loading state while query executes

### 2. Output Section
- **Generated SQL**: Display in syntax-highlighted code block
- **Results Table**: Render query results as HTML table
- **Error Display**: Show errors clearly (validation errors, execution errors, rate limits)

### 3. States to Handle
- `idle`: Initial state, ready for input
- `loading`: Query in progress
- `success`: Show SQL + results
- `error`: Show error message

## API Integration

### Endpoint
```
POST /query
Content-Type: application/json

Request:
{
  "query": "How many taxi trips in the last 24 hours?"
}

Response (success):
{
  "success": true,
  "sql": "SELECT count() FROM nyc_taxi_trips WHERE ...",
  "data": [{"count()": 12345}],
  "columns": ["count()"],
  "row_count": 1,
  "elapsed_ms": 45.2
}

Response (error):
{
  "success": false,
  "error": "Invalid column: foo",
  "sql": null,
  "data": []
}
```

### Backend URL
- Development: `http://localhost:8000`
- Production: Set via environment variable `VITE_API_URL`

## Component Structure

```
src/
  App.svelte        # Main app component
  lib/
    QueryInput.svelte   # Textarea + button
    SqlDisplay.svelte   # Code block for SQL
    ResultsTable.svelte # Table for results
    ErrorMessage.svelte # Error display
  api.js            # API client
  main.js           # Entry point
```

## UI Layout (Simple)

```
┌─────────────────────────────────────┐
│  NL → ClickHouse SQL                │
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐  │
│  │ Enter your question...        │  │
│  │                               │  │
│  └───────────────────────────────┘  │
│  [Run Query]                        │
├─────────────────────────────────────┤
│  Generated SQL:                     │
│  ┌───────────────────────────────┐  │
│  │ SELECT count() FROM ...       │  │
│  └───────────────────────────────┘  │
├─────────────────────────────────────┤
│  Results (1 row, 45ms):             │
│  ┌───────────────────────────────┐  │
│  │ count()                       │  │
│  │ ─────────                     │  │
│  │ 12345                         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Setup Commands

```bash
cd frontend
npm create vite@latest . -- --template svelte
npm install
npm run dev
```

## Example Queries to Test
1. "How many taxi trips are in the database?"
2. "What is the average fare amount?"
3. "Show total revenue in the last 24 hours"
4. "Count trips by payment type"
5. "What's the max tip amount?"

## Non-Goals
- No auth/login
- No query history
- No dark mode (unless trivial)
- No complex state management

## Deliverables
1. Working Svelte app that calls backend `/query` endpoint
2. Clean, simple UI
3. Proper loading and error states
4. Ready for deployment to Vercel/Netlify
