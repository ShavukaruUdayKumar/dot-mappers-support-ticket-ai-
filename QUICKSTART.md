# QUICKSTART GUIDE

## For Evaluator: Run the System in 3 Steps

### Step 1: Get Groq API Key (30 seconds)

1. Go to https://console.groq.com
2. Sign up (free)
3. Generate API key from "API Keys" tab

### Step 2: Configure

```bash
# Copy the example environment file
copy .env.example .env

# Edit .env and paste your API key:
# GROQ_API_KEY=gsk_your_key_here
```

### Step 3: Run

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

Server starts at: **http://localhost:8000**

Interactive docs: **http://localhost:8000** (opens Swagger UI automatically)

---

## Test the System

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Query Example

```bash
curl -X POST http://localhost:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\": \"How many critical tickets are unresolved?\"}"
```

(Remove `^` and use `\` on Unix/Linux/macOS)

### 3. Anomaly Detection

```bash
curl http://localhost:8000/anomalies
```

### 4. Dataset Stats

```bash
curl http://localhost:8000/stats
```

---

## Or Use the Interactive Docs

Open http://localhost:8000 in your browser and test all endpoints with the Swagger UI.

---

## Sample Questions to Try

- "How many tickets are currently open?"
- "Which agent resolved the most tickets?"
- "What is the average rating for Technical category tickets?"
- "Show me all Critical tickets"
- "Which agent has the lowest average rating?"
- "How many billing tickets are escalated?"

---

## Stopping the Server

Press `Ctrl+C` in the terminal running uvicorn.

---

## Troubleshooting

**Problem**: "GROQ_API_KEY not found"
**Solution**: Make sure you created `.env` file (not `.env.example`) and added your key

**Problem**: "Data file not found"
**Solution**: Ensure `data/support_tickets.csv` exists

**Problem**: Port 8000 already in use
**Solution**: Run with different port: `uvicorn app.main:app --port 8001`

---

## Architecture Walkthrough Prep

When explaining the system:

1. **Start with architecture diagram** (see README.md)
2. **Show Swagger UI** at http://localhost:8000
3. **Execute a live query** to demonstrate the flow
4. **Show the anomaly detection** output
5. **Explain design decisions** (why structured JSON, why hybrid anomaly detection)
6. **Discuss scalability** (Pandas → PostgreSQL, add Redis cache, etc.)
