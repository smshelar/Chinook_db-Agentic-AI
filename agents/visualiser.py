"""
agents/visualiser.py
---------------------
Agent 3 — Visualiser
Responsibility: Inspect the DataFrame returned by the Executor and
                produce the most appropriate Plotly chart.

How it decides what chart to use:
- Asks Gemini to look at column names + dtypes and pick a chart type
- Falls back to a simple table if no chart makes sense
- Always returns a plotly Figure object (Streamlit can render these)
"""

import json
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai

from utils.logger import get_logger

log = get_logger("Visualiser")

CHART_TYPES = ["bar", "line", "pie", "scatter", "table"]


class VisualiserAgent:
    """Converts a DataFrame into the most suitable Plotly chart."""

    SYSTEM_PROMPT = """
You are a data visualisation assistant. Given a table of data, your job is
to decide the best chart type and which columns to use.

Respond ONLY with valid JSON — no explanation, no markdown fences.
Format:
{{
  "chart_type": "bar" | "line" | "pie" | "scatter" | "table",
  "x": "column_name_for_x_axis",
  "y": "column_name_for_y_axis",
  "title": "A short descriptive chart title"
}}

Chart type guide:
- bar: comparing categories (e.g. artists by sales)
- line: trends over time (e.g. monthly revenue)
- pie: proportions with few categories (<= 8)
- scatter: two numeric columns with a relationship
- table: when data doesn't suit a chart (e.g. raw text results)

Available columns and dtypes: {column_info}
First 3 rows of data: {sample_rows}
"""

    def __init__(self, model: genai.GenerativeModel):
        self.model = model

    def run(self, df: pd.DataFrame, user_question: str) -> go.Figure:
        """
        Args:
            df: DataFrame of query results.
            user_question: Original user question (for context).
        Returns:
            A Plotly Figure object ready to display in Streamlit.
        """
        log.info("Choosing chart type...")

        column_info = {col: str(df[col].dtype) for col in df.columns}
        sample_rows = df.head(3).to_dict(orient="records")

        prompt = self.SYSTEM_PROMPT.format(
            column_info=json.dumps(column_info),
            sample_rows=json.dumps(sample_rows, default=str),
        )

        response = self.model.generate_content(prompt)
        config = self._parse_config(response.text)

        log.info(f"Chart config: {config}")
        fig = self._build_chart(df, config)
        return fig

    def _parse_config(self, raw: str) -> dict:
        """Parse Gemini's JSON response, with a safe fallback."""
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\n?```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Could not parse chart config — defaulting to table.")
            return {"chart_type": "table", "title": "Results"}

    def _build_chart(self, df: pd.DataFrame, config: dict) -> go.Figure:
        """Build the Plotly figure based on the config."""
        chart_type = config.get("chart_type", "table")
        x = config.get("x")
        y = config.get("y")
        title = config.get("title", "Query Results")

        # Verify columns exist before plotting
        cols = df.columns.tolist()
        if x and x not in cols:
            x = cols[0] if cols else None
        if y and y not in cols:
            y = cols[1] if len(cols) > 1 else cols[0]

        try:
            if chart_type == "bar":
                fig = px.bar(df, x=x, y=y, title=title, text_auto=True)
            elif chart_type == "line":
                fig = px.line(df, x=x, y=y, title=title, markers=True)
            elif chart_type == "pie":
                fig = px.pie(df, names=x, values=y, title=title)
            elif chart_type == "scatter":
                fig = px.scatter(df, x=x, y=y, title=title)
            else:
                fig = go.Figure(
                    data=[go.Table(
                        header=dict(values=list(df.columns), align="left"),
                        cells=dict(values=[df[c] for c in df.columns], align="left"),
                    )]
                )
                fig.update_layout(title=title)
        except Exception as e:
            log.warning(f"Chart build failed ({e}), falling back to table.")
            fig = go.Figure(
                data=[go.Table(
                    header=dict(values=list(df.columns), align="left"),
                    cells=dict(values=[df[c] for c in df.columns], align="left"),
                )]
            )

        fig.update_layout(
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig
