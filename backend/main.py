"""
FastAPI Backend - NL to ClickHouse SQL API.

Endpoints:
- POST /query: Convert NL to SQL and execute
- GET /health: Health check
"""

import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import generate_sql
from validator import validate_sql
from tinybird import run_query
from schema_registry import load_schema, get_schema_context_for_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load schema
    load_schema()
    logger.info("Schema loaded")
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="NL to ClickHouse SQL",
    description="Convert natural language to ClickHouse SQL using GPT-5 with CFG",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    data: List[Dict] = []
    columns: List[str] = []
    row_count: int = 0
    elapsed_ms: float = 0
    error: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/schema")
async def schema():
    """Return schema context for debugging."""
    return {"schema": get_schema_context_for_llm()}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Convert natural language to SQL and execute against ClickHouse.

    1. Generate SQL using GPT-5 with CFG constraint
    2. Validate SQL (defense-in-depth)
    3. Execute against Tinybird
    4. Return results
    """
    nl_query = request.query.strip()

    if not nl_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Step 1: Generate SQL
    logger.info(f"Generating SQL for: {nl_query}")
    gen_result = generate_sql(nl_query)

    if not gen_result["success"]:
        return QueryResponse(
            success=False,
            error=f"SQL generation failed: {gen_result['error']}"
        )

    sql = gen_result["sql"]
    logger.info(f"Generated SQL: {sql}")

    # Step 2: Validate SQL
    is_valid, errors = validate_sql(sql)
    if not is_valid:
        return QueryResponse(
            success=False,
            sql=sql,
            error=f"SQL validation failed: {', '.join(errors)}"
        )

    # Step 3: Execute query
    logger.info(f"Executing SQL: {sql}")
    exec_result = run_query(sql)

    if not exec_result["success"]:
        return QueryResponse(
            success=False,
            sql=sql,
            error=f"Query execution failed: {exec_result['error']}"
        )

    return QueryResponse(
        success=True,
        sql=sql,
        data=exec_result["data"],
        columns=exec_result["columns"],
        row_count=exec_result["row_count"],
        elapsed_ms=exec_result["elapsed_ms"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
