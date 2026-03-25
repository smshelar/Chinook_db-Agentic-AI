# Chinook Agentic AI — Practice Project

A multi-agent AI system that lets you query the Chinook music database using plain English.
Built with Google Gemini (free), SQLite, Streamlit, and Python.

## Architecture

```
User Prompt
    ↓
Orchestrator Agent   ← routes and coordinates
    ↓         ↓         ↓
SQL Writer  Executor  Visualiser
    ↓         ↓         ↓
         Chinook DB     Plotly Chart
```

## Use Case

**"Which artists generated the most revenue in 2009?"**

1. SQL Writer agent reads your question and writes the SQL query
2. Executor agent runs the query safely on Chinook.db
3. Visualiser agent takes the results and creates a bar chart
4. Orchestrator returns everything to the Streamlit UI

## Project Structure

```
chinook_agentic_ai/
├── app.py                  # Streamlit frontend
├── agents/
│   ├── orchestrator.py     # Master coordinator agent
│   ├── sql_writer.py       # NL → SQL agent
│   ├── executor.py         # SQL runner agent
│   └── visualiser.py       # Data → chart agent
├── utils/
│   ├── db.py               # DB connection + schema helper
│   └── logger.py           # Simple logging
├── tests/
│   ├── test_sql_writer.py  # Unit tests for SQL agent
│   ├── test_executor.py    # Unit tests for executor
│   └── test_pipeline.py    # Integration + holdout set tests
├── chinook.db              # SQLite Chinook database
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/YOUR_USERNAME/chinook-agentic-ai.git
cd chinook-agentic-ai
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get your free Gemini API key

- Go to https://aistudio.google.com/app/apikey
- Click "Create API Key" — it's free, no credit card needed
- Copy the key

### 3. Set up your .env file

```bash
cp .env.example .env
# Open .env and paste your key
GEMINI_API_KEY=your_key_here
```

### 4. Download Chinook database

```bash
# Download chinook.db (SQLite version)
# From: https://github.com/lerocha/chinook-database/releases
# Place chinook.db in the project root
```

### 5. Run the app

```bash
streamlit run app.py
```

### 6. Run tests

```bash
pytest tests/ -v
```

## IDE Recommendation

Use **VS Code** for this project:
- Better Python + Streamlit live reload support
- GitLens extension for GitHub integration
- Python extension auto-detects your venv
- Streamlit extension for in-editor preview

Recommended VS Code extensions:
- Python (Microsoft)
- Pylance
- GitLens
- SQLite Viewer (to explore chinook.db visually)
- Python Test Explorer

## Example Queries to Try

- "Show me the top 5 selling artists"
- "Which genre has the most tracks?"
- "What were total sales by country in 2022?"
- "List all albums by AC/DC"
- "Show monthly revenue for 2023"
