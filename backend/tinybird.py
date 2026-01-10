"""
Tinybird Client - Execute SQL queries against Tinybird.

Uses Tinybird's SQL API to run queries and return results.
"""

import os
import time
import httpx
from typing import Any, Dict, List, Optional

from schema_registry import get_default_limit, get_max_limit


class TinybirdClient:
    """Client for executing SQL queries against Tinybird."""

    def __init__(self, token: Optional[str] = None, host: Optional[str] = None):
        self.token = token or os.getenv("TINYBIRD_TOKEN")
        self.host = host or os.getenv("TINYBIRD_HOST", "https://api.tinybird.co")

        if not self.token:
            raise ValueError("TINYBIRD_TOKEN is required")

        self.client = httpx.Client(
            base_url=self.host,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30.0
        )

    def execute(self, sql: str) -> Dict[str, Any]:
        """
        Execute a SQL query and return results.

        Args:
            sql: The SQL query to execute

        Returns:
            dict with keys:
                - success: bool
                - data: list of row dicts
                - columns: list of column names
                - row_count: number of rows returned
                - elapsed_ms: execution time in milliseconds
                - error: error message if failed
        """
        start_time = time.time()

        try:
            response = self.client.post(
                "/v0/sql",
                params={"q": sql}
            )
            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                return {
                    "success": False,
                    "data": [],
                    "columns": [],
                    "row_count": 0,
                    "elapsed_ms": elapsed_ms,
                    "error": f"Tinybird error {response.status_code}: {response.text}"
                }

            result = response.json()

            # Tinybird returns {"data": [...], "meta": [...], ...}
            data = result.get("data", [])
            meta = result.get("meta", [])
            columns = [col["name"] for col in meta] if meta else []

            return {
                "success": True,
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "elapsed_ms": elapsed_ms,
                "error": None
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "elapsed_ms": (time.time() - start_time) * 1000,
                "error": "Query timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "elapsed_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Singleton instance
_client: Optional[TinybirdClient] = None


def get_client() -> TinybirdClient:
    """Get or create the Tinybird client singleton."""
    global _client
    if _client is None:
        _client = TinybirdClient()
    return _client


def run_query(sql: str) -> Dict[str, Any]:
    """
    Execute a SQL query using the singleton client.

    Convenience function that wraps TinybirdClient.execute().
    """
    return get_client().execute(sql)


if __name__ == "__main__":
    if not os.getenv("TINYBIRD_TOKEN"):
        print("Error: TINYBIRD_TOKEN not set")
        exit(1)

    result = run_query("SELECT 1")
    print(f"Test query result: {result}")
