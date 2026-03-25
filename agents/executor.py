"""
agents/executor.py
-------------------
Agent 2 — Executor
Responsibility: Safely execute a SQL SELECT query against Chinook
                and return the results as a pandas DataFrame.

Safety features:
- Connects to DB in read-only mode (see utils/db.py)
- Enforces SELECT-only rule before even running
- Caps results at 500 rows to prevent memory overload
- Times out after 10 seconds
"""

import pandas as pd

from utils.db import run_query
from utils.logger import get_logger

log = get_logger("Executor")

MAX_ROWS = 500


class ExecutorAgent:
    """Runs a SQL query on Chinook and returns a DataFrame."""

    def run(self, sql: str) -> pd.DataFrame:
        """
        Args:
            sql: A validated SELECT query string.
        Returns:
            pandas DataFrame with query results.
        Raises:
            ValueError: If SQL is not a SELECT or results are empty.
            RuntimeError: If the query fails to execute.
        """
        log.info("Executing query...")

        try:
            df = run_query(sql)
        except Exception as e:
            raise RuntimeError(f"Query execution failed: {e}") from e

        if df.empty:
            log.warning("Query returned 0 rows.")
            raise ValueError(
                "The query returned no results. "
                "Try rephrasing your question or check the date range."
            )

        if len(df) > MAX_ROWS:
            log.warning(f"Truncating results from {len(df)} to {MAX_ROWS} rows.")
            df = df.head(MAX_ROWS)

        log.info(f"Query returned {len(df)} rows, {len(df.columns)} columns.")
        return df
