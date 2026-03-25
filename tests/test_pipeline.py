"""
tests/test_pipeline.py
-----------------------
Integration tests for the full Orchestrator pipeline.

Testing strategy:
- Mock Gemini and DB so the full pipeline runs offline
- Holdout set: 6 end-to-end cases that verify the pipeline produces
  a SQL, a DataFrame, and a Figure for realistic questions
- Each test documents a "slice" of expected behaviour

Run all tests:
    pytest tests/ -v

Run only fast unit tests (skip integration):
    pytest tests/ -v -m "not integration"

Run only integration tests:
    pytest tests/ -v -m integration
"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
import plotly.graph_objects as go

from agents.orchestrator import OrchestratorAgent


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_gemini_model():
    model = MagicMock()
    return model


@pytest.fixture
def orchestrator(mock_gemini_model):
    """
    Orchestrator with all external dependencies mocked:
    - Gemini model (no API calls)
    - DB connection (no chinook.db needed)
    """
    with patch("agents.orchestrator.genai") as mock_genai, \
         patch("agents.orchestrator.os.getenv", return_value="fake-key"):
        mock_genai.GenerativeModel.return_value = mock_gemini_model
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        from agents.sql_writer import SQLWriterAgent
        from agents.executor import ExecutorAgent
        from agents.visualiser import VisualiserAgent
        orch.sql_writer = SQLWriterAgent(model=mock_gemini_model)
        orch.executor = ExecutorAgent()
        orch.visualiser = VisualiserAgent(model=mock_gemini_model)
    return orch


def make_sql_response(sql: str):
    r = MagicMock()
    r.text = sql
    return r


def make_chart_response(chart_type="bar", x="Name", y="Total"):
    import json
    r = MagicMock()
    r.text = json.dumps({
        "chart_type": chart_type,
        "x": x,
        "y": y,
        "title": "Test Chart"
    })
    return r


# ── Holdout pipeline cases ────────────────────────────────────────────────────
# Each case represents a realistic user question.
# We verify the pipeline:
#   1. Produces a valid SQL string
#   2. Returns a non-empty DataFrame
#   3. Returns a Plotly figure
#   4. Reports success=True

PIPELINE_HOLDOUT = [
    {
        "id": "top_artists",
        "question": "Top 5 selling artists by revenue",
        "sql": "SELECT Artist.Name, SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity) AS Total FROM Artist JOIN Album ON Artist.ArtistId = Album.ArtistId JOIN Track ON Album.AlbumId = Track.AlbumId JOIN InvoiceLine ON Track.TrackId = InvoiceLine.TrackId GROUP BY Artist.Name ORDER BY Total DESC LIMIT 5",
        "fake_data": {"Name": ["AC/DC", "Metallica", "U2", "Aerosmith", "Pearl Jam"], "Total": [280, 250, 220, 190, 180]},
        "chart_type": "bar",
        "x_col": "Name",
        "y_col": "Total",
    },
    {
        "id": "genre_count",
        "question": "Which genre has the most tracks?",
        "sql": "SELECT Genre.Name, COUNT(Track.TrackId) AS TrackCount FROM Genre JOIN Track ON Genre.GenreId = Track.GenreId GROUP BY Genre.Name ORDER BY TrackCount DESC LIMIT 10",
        "fake_data": {"Name": ["Rock", "Jazz", "Metal"], "TrackCount": [1297, 130, 374]},
        "chart_type": "bar",
        "x_col": "Name",
        "y_col": "TrackCount",
    },
    {
        "id": "monthly_revenue",
        "question": "Monthly revenue for 2009",
        "sql": "SELECT strftime('%Y-%m', InvoiceDate) AS Month, SUM(Total) AS Revenue FROM Invoice WHERE InvoiceDate LIKE '2009%' GROUP BY Month ORDER BY Month",
        "fake_data": {"Month": ["2009-01", "2009-02", "2009-03"], "Revenue": [38.62, 37.62, 19.8]},
        "chart_type": "line",
        "x_col": "Month",
        "y_col": "Revenue",
    },
    {
        "id": "country_sales",
        "question": "Which country buys the most music?",
        "sql": "SELECT BillingCountry AS Country, SUM(Total) AS Revenue FROM Invoice GROUP BY BillingCountry ORDER BY Revenue DESC LIMIT 10",
        "fake_data": {"Country": ["USA", "Canada", "France"], "Revenue": [523.06, 303.96, 195.1]},
        "chart_type": "bar",
        "x_col": "Country",
        "y_col": "Revenue",
    },
    {
        "id": "acdc_albums",
        "question": "Show all albums by AC/DC",
        "sql": "SELECT Album.Title FROM Album JOIN Artist ON Album.ArtistId = Artist.ArtistId WHERE Artist.Name = 'AC/DC'",
        "fake_data": {"Title": ["For Those About To Rock", "Let There Be Rock"]},
        "chart_type": "table",
        "x_col": "Title",
        "y_col": "Title",
    },
    {
        "id": "top_customers",
        "question": "Top 10 customers by total spend",
        "sql": "SELECT Customer.FirstName || ' ' || Customer.LastName AS Customer, SUM(Invoice.Total) AS Spend FROM Customer JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId GROUP BY Customer.CustomerId ORDER BY Spend DESC LIMIT 10",
        "fake_data": {"Customer": ["Helena Holý", "Richard Cunningham"], "Spend": [49.62, 47.62]},
        "chart_type": "bar",
        "x_col": "Customer",
        "y_col": "Spend",
    },
]


@pytest.mark.parametrize("case", PIPELINE_HOLDOUT, ids=[c["id"] for c in PIPELINE_HOLDOUT])
def test_pipeline_holdout(orchestrator, mock_gemini_model, case):
    """
    Full pipeline holdout test.
    For each realistic question, we check the pipeline:
    - Generates a SQL query
    - Gets data back
    - Produces a chart
    - Returns success
    """
    fake_df = pd.DataFrame(case["fake_data"])

    # Make SQL writer return our test SQL
    mock_gemini_model.generate_content.side_effect = [
        make_sql_response(case["sql"]),
        make_chart_response(case["chart_type"], case["x_col"], case["y_col"]),
    ]

    with patch("agents.executor.run_query", return_value=fake_df):
        result = orchestrator.run(case["question"])

    # Verify success
    assert result.success is True, f"Pipeline failed: {result.error}"

    # Verify SQL was generated
    assert result.sql is not None
    assert "SELECT" in result.sql.upper()

    # Verify DataFrame
    assert result.dataframe is not None
    assert not result.dataframe.empty

    # Verify figure
    assert result.figure is not None
    assert isinstance(result.figure, go.Figure)


class TestOrchestratorErrorHandling:
    """Test that the orchestrator handles failures gracefully."""

    def test_sql_writer_failure_returns_error(self, orchestrator, mock_gemini_model):
        mock_gemini_model.generate_content.return_value = make_sql_response(
            "DROP TABLE Artist"  # will fail validation
        )
        result = orchestrator.run("drop the artists table")
        assert result.success is False
        assert result.error is not None
        assert "SQL Writer failed" in result.error

    def test_executor_failure_returns_error(self, orchestrator, mock_gemini_model):
        mock_gemini_model.generate_content.return_value = make_sql_response(
            "SELECT * FROM Artist LIMIT 5"
        )
        with patch("agents.executor.run_query", side_effect=Exception("DB error")):
            result = orchestrator.run("list artists")
        assert result.success is False
        assert "Executor failed" in result.error

    def test_empty_result_returns_error(self, orchestrator, mock_gemini_model):
        mock_gemini_model.generate_content.return_value = make_sql_response(
            "SELECT * FROM Artist WHERE 1=0"
        )
        with patch("agents.executor.run_query", return_value=pd.DataFrame()):
            result = orchestrator.run("impossible query")
        assert result.success is False
