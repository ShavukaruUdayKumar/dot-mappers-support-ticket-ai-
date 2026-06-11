# Support Ticket AI System

AI-powered customer support ticket analysis with natural language querying and hybrid anomaly detection.

---

## Architecture

```
User
  │
  ▼
FastAPI (app/main.py)
  │
  ├── POST /query       ──► QueryService ──► LLMService (NL → JSON Intent)
  │                                      ──► Pandas Executor (Intent → Data)
  │                                      ──► LLMService (Data → NL Answer)
  │
  ├── GET  /anomalies   ──► AnomalyService ──► Rule-based detectors
  │                                        ──► Z-score statistical detectors
  │
  ├── GET  /stats       ──► DataLoader (Pandas aggregations)
  ├── GET  /schema      ──► DataLoader (column metadata)
  └── GET  /health      ──► System status
```

### Key Design Decision: LLM as Structured Reasoner

Instead of letting the LLM answer questions directly (hallucination risk), the system uses a two-step approach:

```
Natural Language Question
         │
         ▼
    LLM Call #1
    Converts to structured QueryIntent JSON:
    {
      "intent": "count",
      "filters": {"priority": "Critical", "status": "Open"},
      "aggregations": ["count"],
      "group_by": null
    }
         │
         ▼
    Pandas Executor (deterministic, exact)
         │
         ▼
    LLM Call #2
    Converts raw result to natural language answer
```

This separates **reasoning** (LLM) from **computation** (Pandas) — eliminating hallucinated counts or wrong aggregations.

---

## Tech Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| API Framework | FastAPI | Fast, auto-docs, async |
| Data Layer | Pandas | Sufficient for 500 rows, simple interface |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, fast, high quality |
| Validation | Pydantic v2 | Type safety everywhere |
| Anomaly Detection | Rule-based + SciPy Z-score | Deterministic + statistical |
| Config | pydantic-settings | 12-factor app config |

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd support-ticket-ai

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Get a free Groq API key at: https://console.groq.com

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

API available at: http://localhost:8000

Interactive docs: http://localhost:8000 (Swagger UI)

### 3b. Run the Streamlit UI (optional)

```bash
streamlit run streamlit_app.py
```

UI available at: http://localhost:8501

### 4. Run with Docker (optional)

```bash
docker-compose up --build
```

---

## API Endpoints

### `GET /health`
Returns system health and LLM service info.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "data_loaded": true,
  "total_tickets": 441,
  "llm_service": "llama-3.3-70b-versatile",
  "uptime_seconds": 0.0
}
```

---

### `POST /query`
Natural language question against the dataset.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many critical tickets are currently open?"}'
```

```json
{
  "question": "How many critical tickets are currently open?",
  "natural_answer": "There are 12 critical tickets currently open.",
  "data": 12,
  "metadata": {
    "execution_time_ms": 1243.5,
    "rows_returned": 1,
    "query_intent": {
      "intent": "count",
      "filters": {"priority": "Critical", "status": "Open"},
      "aggregations": ["count"],
      "group_by": null,
      "sort_by": null,
      "order": "desc",
      "limit": null
    },
    "llm_calls": 2
  }
}
```

---

### `GET /anomalies`
Runs hybrid anomaly detection and returns all findings.

```bash
curl http://localhost:8000/anomalies | python -m json.tool
```

```json
{
  "total_anomalies": 23,
  "anomalies_by_type": {
    "stale_critical_ticket": 8,
    "resolution_time_outlier": 7,
    "stale_high_priority_ticket": 5,
    "low_agent_rating": 3
  },
  "critical_anomalies": [
    {
      "ticket_id": "TKT-022",
      "anomaly_type": "stale_critical_ticket",
      "severity": "critical",
      "reason": "Critical priority ticket open for 1847.2 hours (threshold: 24h)",
      "metadata": {
        "age_hours": 1847.2,
        "priority": "Critical",
        "category": "Technical",
        "agent_id": "AGT-11"
      }
    }
  ],
  "high_anomalies": [...],
  "medium_anomalies": [...],
  "low_anomalies": [...]
}
```

---

### `GET /stats`
Dataset-wide statistics.

```bash
curl http://localhost:8000/stats
```

```json
{
  "total_tickets": 441,
  "open_tickets": 120,
  "resolved_tickets": 240,
  "escalated_tickets": 81,
  "avg_resolution_time_hrs": 18.4,
  "avg_response_time_hrs": 2.6,
  "avg_customer_rating": 3.6,
  "tickets_by_category": {"General": 170, "Billing": 150, "Technical": 121},
  "tickets_by_priority": {"Low": 140, "Medium": 140, "High": 120, "Critical": 41},
  "tickets_by_status": {"Resolved": 240, "Open": 120, "Escalated": 81},
  "top_agents_by_resolution": [
    {"agent_id": "AGT-07", "resolved_count": 28}
  ]
}
```

---

### `GET /schema`
Dataset column metadata (useful for debugging).

```bash
curl http://localhost:8000/schema
```

---

## Example Queries

All queries tested against the dataset:

| Question | Expected Behaviour |
|----------|--------------------|
| `"How many tickets are currently open?"` | Returns exact count |
| `"Which agent resolved the most tickets?"` | Returns agent_id + count |
| `"What is the average rating for Technical tickets?"` | Returns float |
| `"Show all Critical tickets"` | Returns filtered list |
| `"How many billing tickets are escalated?"` | Returns count with two filters |
| `"Which agent has the lowest average rating?"` | Groups by agent, sorts ascending |

---

## Anomaly Detection Design

Two complementary approaches:

### Rule-Based (Business Logic)
| Rule | Severity |
|------|----------|
| Critical ticket open > 24 hours | Critical |
| High priority ticket open > 48 hours | High |
| Agent avg rating < 2.5 (min 5 tickets) | Medium |

### Statistical (Z-Score)
| Detection | Method | Threshold |
|-----------|--------|-----------|
| Resolution time outliers | Z-score per category | \|z\| > 3 |
| Response time outliers | Global Z-score | \|z\| > 3 |

Combining both catches **known failure patterns** (rules) and **unknown anomalies** (statistics).

---

## Running Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## Design Decisions & Trade-offs

### Why Pandas and not SQL/DuckDB?
For 500 rows, Pandas is simpler and faster to develop. The DataLoader and QueryService are designed with an interface that can swap Pandas for DuckDB or PostgreSQL without changing the API contract.

### Why Groq and not Ollama?
Groq free tier gives production-quality inference (llama3-70b) with zero local setup. An evaluator can run this at zero cost without needing GPU hardware. The LLMService abstraction makes switching trivial.

### Why structured JSON output from LLM?
Direct LLM answers hallucinate counts and statistics. The JSON intent approach is auditable — you can log exactly what query was executed and trace any wrong answer.

### Why Z-score over IQR?
Z-score is more intuitive to explain in a walkthrough ("3 standard deviations") and works well for near-normal distributions like resolution times. With more data, an Isolation Forest would be stronger.

---

## Future Improvements

With more time:

- **PostgreSQL** backend for production scale
- **Redis** cache for repeated queries
- **LangGraph** multi-step reasoning for complex analytical questions
- **Vector search** on `issue_summary` for semantic similarity
- **OpenTelemetry** observability (traces per LLM call)
- **Rate limiting** and JWT authentication
- **Streaming** responses for large result sets
- **Fine-tuned intent classifier** to replace LLM for common query patterns
