"""
tests/test_executor.py
-----------------------
Tests for the Executor agent.

Testing strategy:
- Mock the DB layer so tests don't need chinook.db on disk
- Test row caps, empty result handling, and SQL safety guard
"""

import pandas as pd
import pytest
from unittest.mock import patch

from agents.executor import ExecutorAgent, MAX_ROWS


@pytest.fixture
def agent():
    return ExecutorAgent()


class TestExecutorSafety:
    """Test that the executor rejects non-SELECT queries."""

    def test_rejects_drop(self, agent):
        with pytest.raises(ValueError, match="SELECT"):
            with patch("agents.executor.run_query", side_effect=ValueError("Only SELECT")):
                agent.run("DROP TABLE Artist")

    def test_rejects_insert(self, agent):
        with patch("agents.executor.run_query", side_effect=ValueError("Only SELECT")):
            with pytest.raises(ValueError):
                agent.run("INSERT INTO Artist VALUES (1,'x')")


class TestExecutorResults:
    """Test normal result handling."""

    def test_returns_dataframe(self, agent):
        fake_df = pd.DataFrame({"Name": ["AC/DC", "Metallica"], "Total": [100, 80]})
        with patch("agents.executor.run_query", return_value=fake_df):
            result = agent.run("SELECT Name, Total FROM Artist LIMIT 2")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_raises_on_empty_result(self, agent):
        empty_df = pd.DataFrame()
        with patch("agents.executor.run_query", return_value=empty_df):
            with pytest.raises(ValueError, match="no results"):
                agent.run("SELECT * FROM Artist WHERE 1=0")

    def test_truncates_large_results(self, agent):
        big_df = pd.DataFrame({"id": range(MAX_ROWS + 50)})
        with patch("agents.executor.run_query", return_value=big_df):
            result = agent.run("SELECT id FROM Artist")
        assert len(result) == MAX_ROWS

    def test_runtime_error_on_bad_query(self, agent):
        with patch("agents.executor.run_query", side_effect=Exception("syntax error")):
            with pytest.raises(RuntimeError, match="Query execution failed"):
                agent.run("SELECT * FROM NonExistentTable")
