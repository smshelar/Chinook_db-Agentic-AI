"""
agents/orchestrator.py
-----------------------
Orchestrator Agent — the "brain" of the pipeline.
Responsibility: Accept the user's question, call each specialist agent
                in the right order, handle errors gracefully, and return
                a structured result to the Streamlit UI.

Pipeline:
  user_question
      → SQLWriterAgent  → sql
      → ExecutorAgent   → dataframe
      → VisualiserAgent → plotly_figure
      → return result dict
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from dotenv import load_dotenv

from agents.sql_writer import SQLWriterAgent
from agents.executor import ExecutorAgent
from agents.visualiser import VisualiserAgent
from utils.logger import get_logger

load_dotenv()
log = get_logger("Orchestrator")


@dataclass
class PipelineResult:
    """Everything the Streamlit UI needs in one object."""
    success: bool
    user_question: str
    sql: Optional[str] = None
    dataframe: Optional[pd.DataFrame] = None
    figure: Optional[go.Figure] = None
    error: Optional[str] = None
    steps: list = field(default_factory=list)  # Log of what happened


class OrchestratorAgent:
    """Coordinates the full agentic pipeline."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found. "
                "Copy .env.example to .env and add your key."
            )
        genai.configure(api_key=api_key)
        # Using gemini-2.5-flash-lite — free tier, fast, great for structured tasks
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        self.sql_writer = SQLWriterAgent(model=model)
        self.executor = ExecutorAgent()
        self.visualiser = VisualiserAgent(model=model)

    def run(self, user_question: str) -> PipelineResult:
        """
        Run the full pipeline for a user question.

        Args:
            user_question: Natural language question from the user.
        Returns:
            PipelineResult with all outputs or an error message.
        """
        result = PipelineResult(success=False, user_question=user_question)
        log.info(f"=== Pipeline START: '{user_question}' ===")

        # Step 1: Write SQL
        try:
            result.steps.append("Writing SQL query...")
            sql = self.sql_writer.run(user_question)
            result.sql = sql
            result.steps.append(f"SQL ready: {sql[:80]}...")
        except Exception as e:
            result.error = f"SQL Writer failed: {e}"
            log.error(result.error)
            return result

        # Step 2: Execute SQL
        try:
            result.steps.append("Executing query on Chinook DB...")
            df = self.executor.run(sql)
            result.dataframe = df
            result.steps.append(f"Got {len(df)} rows back.")
        except Exception as e:
            result.error = f"Executor failed: {e}"
            log.error(result.error)
            return result

        # Step 3: Visualise
        try:
            result.steps.append("Building visualisation...")
            fig = self.visualiser.run(df, user_question)
            result.figure = fig
            result.steps.append("Chart ready.")
        except Exception as e:
            # Visualisation failure is non-fatal — return the data at least
            log.warning(f"Visualiser failed: {e}. Returning data only.")
            result.steps.append("Chart failed — showing table instead.")

        result.success = True
        log.info("=== Pipeline COMPLETE ===")
        return result
