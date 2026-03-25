"""
agents/sql_writer.py
---------------------
Agent 1 — SQL Writer
Responsibility: Turn the user's natural language prompt into a valid
                SQLite SELECT query against the Chinook database.

How it works:
  1. Receives the user's plain-English question
  2. Builds a prompt that includes the full Chinook schema
  3. Calls Gemini to generate a SQL query
  4. Strips markdown fences and returns raw SQL
"""

import re
import google.generativeai as genai

from utils.db import get_schema_description
from utils.logger import get_logger

log = get_logger("SQLWriter")


class SQLWriterAgent:
    """Converts a natural language question into a Chinook SQL query."""

    SYSTEM_PROMPT = """
You are a SQL expert assistant. Your ONLY job is to write a valid SQLite
SELECT query that answers the user's question using the Chinook database.

Rules:
- Only output the raw SQL query — no explanation, no markdown fences.
- Always use SELECT. Never use INSERT, UPDATE, DELETE, DROP, or CREATE.
- Use proper SQLite syntax (e.g. strftime for dates).
- For date filtering, always use: strftime('%Y', InvoiceDate) = '2009' NOT InvoiceDate LIKE '2009%'.
- Limit results to 100 rows unless the user asks for all data.
- Use aliases to make column names readable (e.g. AS "Artist Name").
- Always use double quotes for column aliases in ORDER BY, never single quotes. Example: ORDER BY "Total Revenue" DESC
- The database contains data from 2021 to 2025 only. Never filter for years outside this range.

Database schema:
{schema}
"""

    def __init__(self, model: genai.GenerativeModel):
        self.model = model
        self.schema = get_schema_description()

    def run(self, user_question: str) -> str:
        """
        Args:
            user_question: Plain English question from the user.
        Returns:
            A SQL SELECT query string.
        Raises:
            ValueError: If the generated query looks unsafe.
        """
        log.info(f"Writing SQL for: '{user_question}'")

        system = self.SYSTEM_PROMPT.format(schema=self.schema)
        full_prompt = f"{system}\n\nQuestion: {user_question}"

        response = self.model.generate_content(full_prompt)
        sql = self._clean_sql(response.text)
        print("DEBUG SQL:", sql) 
        log.info(f"Generated SQL:\n{sql}")
        self._validate(sql)
        return sql

    def _clean_sql(self, raw: str) -> str:
        """Strip markdown code fences if Gemini wraps the output."""
        raw = raw.strip()
        # Remove ```sql ... ``` or ``` ... ```
        raw = re.sub(r"^```(?:sql)?\n?", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\n?```$", "", raw)
        return raw.strip()

    def _validate(self, sql: str) -> None:
        """Basic safety check — only SELECT queries allowed."""
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]
        upper = sql.upper()
        for word in forbidden:
            if word in upper:
                raise ValueError(
                    f"Unsafe SQL detected — contains '{word}'. Aborting."
                )
        if not upper.strip().startswith("SELECT"):
            raise ValueError("Generated query does not start with SELECT.")
