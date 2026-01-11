"""
FastAPI Backend - NL to ClickHouse SQL API.

Endpoints:
- POST /query: Convert NL to SQL and execute
- GET /health: Health check
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import generate_sql
from schema_registry import get_default_limit, get_max_limit
from validator import validate_sql, enforce_limit
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

frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)
allowed_origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    schema: Optional[str] = None


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
async def schema(schema: Optional[str] = None):
    """Return schema context for debugging."""
    schema_name = schema or "default"
    return {"schema": get_schema_context_for_llm(schema_name)}


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
    schema_name = request.schema or "default"
    gen_result = generate_sql(nl_query, schema_name=schema_name)

    if not gen_result["success"]:
        return QueryResponse(
            success=False,
            error=f"SQL generation failed: {gen_result['error']}"
        )

    sql = gen_result["sql"]
    logger.info(f"Generated SQL: {sql}")

    # Step 2: Validate SQL
    is_valid, errors = validate_sql(sql, schema_name=schema_name)
    if not is_valid:
        return QueryResponse(
            success=False,
            sql=sql,
            error=f"SQL validation failed: {', '.join(errors)}"
        )

    # Step 3: Enforce LIMIT
    ok, limited_sql, errors = enforce_limit(
        sql,
        default_limit=get_default_limit(schema_name),
        max_limit=get_max_limit(schema_name)
    )
    if not ok:
        return QueryResponse(
            success=False,
            sql=sql,
            error=f"SQL limit enforcement failed: {', '.join(errors)}"
        )
    sql = limited_sql

    # Step 4: Execute query
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
