# Sample Questions & Expected Answers

All questions tested against the real dataset (`data/support_tickets.csv`, 500 rows).
These are verified exact answers — not estimates.

---

## How to Test

1. Start the server: `uvicorn app.main:app --reload`
2. Open Streamlit UI: `streamlit run streamlit_app.py`
3. Go to **Tab 1 → Ask a Question**
4. Type any question below and verify the answer matches

Or via API:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many tickets are currently open?\"}"
```

---

## Count Questions

| # | Question | Expected Answer |
|---|----------|----------------|
| 1 | How many tickets are currently open? | **111** |
| 2 | How many critical tickets are open? | **9** |
| 3 | How many tickets are escalated? | **62** |
| 4 | How many High priority tickets are resolved? | **85** |
| 5 | How many General category tickets are open? | **39** |
| 6 | How many Medium priority tickets exist? | **169** |
| 7 | How many Billing tickets are resolved? | **101** |
| 8 | How many Low priority tickets are open? | **28** |
| 9 | How many Technical tickets are escalated? | **18** |
| 10 | How many tickets have a customer rating of 5? | **95** |
| 11 | How many tickets have no customer rating? | **173** |
| 12 | How many tickets does AGT-05 have? | **27** |

---

## Average / Aggregate Questions

| # | Question | Expected Answer |
|---|----------|----------------|
| 13 | What is the average response time in hours? | **2.62 hrs** |
| 14 | What is the average resolution time for Critical tickets? | **10.63 hrs** |
| 15 | What is the average customer rating for Billing tickets? | **3.72 / 5** |
| 16 | What is the average customer rating for Technical tickets? | **3.74 / 5** |

---

## Top / Group Questions

| # | Question | Expected Answer |
|---|----------|----------------|
| 17 | Which agent resolved the most tickets? | **AGT-09 with 37 resolved tickets** |
| 18 | Which agent has the most tickets assigned? | **AGT-09 with 50 tickets** |
| 19 | Which category has the most escalated tickets? | **General with 28 escalated** |

---

## Dataset Summary (Ground Truth)

```
Total Tickets   : 500
Open            : 111
Resolved        : 327
Escalated       : 62

Priority Breakdown:
  Critical : 55
  High     : 134
  Medium   : 169
  Low      : 142

Category Breakdown:
  Billing   : ~167
  Technical : ~166
  General   : ~167

Avg Resolution Time : 19.16 hrs
Avg Response Time   : 2.62 hrs
Avg Customer Rating : 3.75 / 5
```

---

## Architecture Behind Every Answer

```
Your Question (natural language)
        │
        ▼
   LLM Call #1  — converts question to JSON intent
        │
        ▼
   Pandas Executor  — runs exact computation on CSV
        │
        ▼
   LLM Call #2  — narrates result in plain English
        │
        ▼
   Your Answer (exact, not hallucinated)
```

The CSV data never goes into the LLM prompt.
Only column names and schema go in.
All numbers come from Pandas — deterministic and exact.
