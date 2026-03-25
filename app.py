"""
app.py
-------
Streamlit frontend for the Chinook Agentic AI project.

Run with:
    streamlit run app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from agents.orchestrator import OrchestratorAgent


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chinook Agentic AI",
    page_icon="🎵",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎵 Chinook AI")
    st.caption("Multi-agent SQL assistant")

    st.markdown("### Example questions")
    examples = [
        "Top 5 selling artists by total revenue",
        "Which genre has the most tracks?",
        "Monthly revenue trend for 2022",
        "Show all albums by AC/DC",
        "Top 10 customers by total spend",
        "Which country bought the most music in 2023?",
        "Which artist generated the most revenue in 2023?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

    st.markdown("---")
    st.markdown("**Pipeline**")
    st.markdown(
        "1. 🧠 Orchestrator\n"
        "2. ✍️ SQL Writer\n"
        "3. ▶️ Executor\n"
        "4. 📊 Visualiser"
    )

# ── Main area ─────────────────────────────────────────────────────────────────
st.title("Ask the Chinook Music Database")
st.caption("Powered by Google Gemini · 4 cooperative AI agents")
st.info("📅 Data range: 2021–2025 · Chinook Music Database")

question = st.text_input(
    "Your question",
    value=st.session_state.get("question", ""),
    placeholder="e.g. Which artists generated the most revenue in 2022?",
    key="question_input",
)

run_button = st.button("Ask ✦", type="primary", use_container_width=False)

if run_button and question.strip():
    # Clear previous question from session state
    st.session_state.pop("question", None)

    # Initialise orchestrator (cached in session)
    if "orchestrator" not in st.session_state:
        with st.spinner("Starting agents..."):
            try:
                st.session_state["orchestrator"] = OrchestratorAgent()
            except EnvironmentError as e:
                st.error(str(e))
                st.stop()

    orchestrator = st.session_state["orchestrator"]

    # Run the pipeline
    with st.spinner("🤖 Agents at work..."):
        result = orchestrator.run(question)

    # ── Show pipeline steps (expander) ──────────────────────────────────────
    with st.expander("Pipeline steps", expanded=False):
        for step in result.steps:
            st.markdown(f"- {step}")

    # ── Error state ──────────────────────────────────────────────────────────
    if not result.success:
        if "no results" in str(result.error).lower():
            st.warning("🔍 No data found for your question. Try rephrasing or use a different year (2021–2025).")
        elif "sql writer failed" in str(result.error).lower():
            st.warning("🤔 I couldn't understand that question. Try asking something like 'Top 5 selling artists' or 'Monthly revenue for 2022'.")
        elif "executor failed" in str(result.error).lower():
            st.warning("⚠️ The query didn't return any results. Try a simpler question or check the date range (2021–2025).")
        else:
            st.warning("😕 Something went wrong. Please try rephrasing your question.")
        
        with st.expander("Technical details", expanded=False):
            st.code(result.error)
        st.stop()


    # ── Show SQL ─────────────────────────────────────────────────────────────
    with st.expander("Generated SQL", expanded=True):
        st.code(result.sql, language="sql")

    # ── Show chart ───────────────────────────────────────────────────────────
    if result.figure:
        st.subheader("Visualisation")
        st.plotly_chart(result.figure, use_container_width=True)

    # ── Show data table ───────────────────────────────────────────────────────
    if result.dataframe is not None:
        st.subheader(f"Data ({len(result.dataframe)} rows)")
        st.dataframe(result.dataframe, use_container_width=True)

elif run_button:
    st.warning("Please enter a question first.")
