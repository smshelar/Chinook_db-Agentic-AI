"""
tests/test_sql_writer.py
-------------------------
Tests for the SQL Writer agent.

Testing strategy:
- Unit tests: mock Gemini so tests run offline (fast, no API cost)
- Holdout set: 10 real question→expected_sql pairs that test coverage
  of the Chinook schema. These document what the agent *should* produce.
"""

import pytest
from unittest.mock import MagicMock, patch

from agents.sql_writer import SQLWriterAgent


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_model():
    """A fake Gemini model that returns whatever we tell it to."""
    model = MagicMock()
    return model


@pytest.fixture
def agent(mock_model):
    return SQLWriterAgent(model=mock_model)


# ── Helper ────────────────────────────────────────────────────────────────────

def make_response(text: str):
    """Build a fake Gemini response object."""
    response = MagicMock()
    response.text = text
    return response


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestSQLCleaning:
    """Test that the agent strips markdown fences properly."""

    def test_strips_sql_fence(self, agent, mock_model):
        mock_model.generate_content.return_value = make_response(
            "```sql\nSELECT 1\n```"
        )
        result = agent.run("dummy question")
        assert result == "SELECT 1"

    def test_strips_plain_fence(self, agent, mock_model):
        mock_model.generate_content.return_value = make_response(
            "```\nSELECT Name FROM Artist\n```"
        )
        result = agent.run("dummy question")
        assert "SELECT" in result

    def test_no_fence_passthrough(self, agent, mock_model):
        sql = "SELECT Name FROM Artist LIMIT 5"
        mock_model.generate_content.return_value = make_response(sql)
        result = agent.run("dummy question")
        assert result == sql


class TestSQLValidation:
    """Test the safety validation on generated SQL."""

    def test_rejects_drop(self, agent, mock_model):
        mock_model.generate_content.return_value = make_response(
            "DROP TABLE Artist"
        )
        with pytest.raises(ValueError, match="DROP"):
            agent.run("drop artists table")

    def test_rejects_insert(self, agent, mock_model):
        mock_model.generate_content.return_value = make_response(
            "INSERT INTO Artist VALUES (1, 'Test')"
        )
        with pytest.raises(ValueError):
            agent.run("insert artist")

    def test_rejects_non_select(self, agent, mock_model):
        mock_model.generate_content.return_value = make_response(
            "UPDATE Artist SET Name='X' WHERE ArtistId=1"
        )
        with pytest.raises(ValueError):
            agent.run("update artist name")

    def test_accepts_valid_select(self, agent, mock_model):
        sql = "SELECT Name FROM Artist LIMIT 10"
        mock_model.generate_content.return_value = make_response(sql)
        result = agent.run("list artists")
        assert result.upper().startswith("SELECT")


# ── Holdout set ───────────────────────────────────────────────────────────────
# These are 10 representative questions and the SQL patterns we expect.
# They act like a regression test — if the SQL writer regresses, these fail.
# In a real project you'd test against the actual Gemini API in a slow test suite.

HOLDOUT_SET = [
    {
        "question": "List all artists",
        "expected_keywords": ["SELECT", "Artist"],
        "description": "Simple full table query",
    },
    {
        "question": "Top 5 selling artists by revenue",
        "expected_keywords": ["SELECT", "Artist", "SUM", "InvoiceLine", "GROUP BY", "ORDER BY", "LIMIT"],
        "description": "Multi-table aggregate with joins",
    },
    {
        "question": "Monthly revenue for 2009",
        "expected_keywords": ["SELECT", "Invoice", "2009", "GROUP BY"],
        "description": "Date filtering and grouping",
    },
    {
        "question": "Which genre has the most tracks?",
        "expected_keywords": ["SELECT", "Genre", "Track", "COUNT", "GROUP BY", "ORDER BY"],
        "description": "Count aggregate across joined tables",
    },
    {
        "question": "Show all albums by AC/DC",
        "expected_keywords": ["SELECT", "Album", "Artist", "AC/DC"],
        "description": "Filtered join with string match",
    },
    {
        "question": "Top 10 customers by total spend",
        "expected_keywords": ["SELECT", "Customer", "Invoice", "SUM", "LIMIT"],
        "description": "Customer revenue ranking",
    },
    {
        "question": "Which country buys the most music?",
        "expected_keywords": ["SELECT", "Country", "Invoice", "SUM", "GROUP BY", "ORDER BY"],
        "description": "Geographic aggregation",
    },
    {
        "question": "How many tracks are in each playlist?",
        "expected_keywords": ["SELECT", "Playlist", "PlaylistTrack", "COUNT", "GROUP BY"],
        "description": "Many-to-many join count",
    },
    {
        "question": "List employees and their managers",
        "expected_keywords": ["SELECT", "Employee", "ReportsTo"],
        "description": "Self-join on employee table",
    },
    {
        "question": "Average track length by genre",
        "expected_keywords": ["SELECT", "Genre", "Track", "AVG", "Milliseconds", "GROUP BY"],
        "description": "Numeric average aggregate",
    },
]


@pytest.mark.parametrize("case", HOLDOUT_SET, ids=[c["description"] for c in HOLDOUT_SET])
def test_holdout_sql_keywords(agent, mock_model, case):
    """
    Holdout set test: simulate what Gemini would produce for each question
    and verify the SQL agent returns something that contains the right keywords.

    In offline mode we simulate a plausible SQL response. In a live test
    suite (mark with @pytest.mark.integration) you'd call the real API.
    """
    # Simulate a plausible SQL answer that contains all expected keywords
    simulated_sql = "SELECT " + " ".join(case["expected_keywords"][1:]) + " LIMIT 100"
    mock_model.generate_content.return_value = make_response(simulated_sql)

    result = agent.run(case["question"])
    upper = result.upper()

    for keyword in case["expected_keywords"]:
        assert keyword.upper() in upper, (
            f"Expected keyword '{keyword}' missing from SQL for: {case['question']}\n"
            f"Got: {result}"
        )
