# Architecture: Solo Dining Recommender

## Overview

A Streamlit app that helps solo diners quickly find suitable restaurants based on their preferences. The core flow: user inputs preferences → AI generates personalized recommendations → results displayed with key details.

---

## Data Model

One main table to store user sessions and recommendation history (SQLite via sqlite3 or a simple JSON file for prototyping):

**recommendations**

| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| created_at | TIMESTAMP | When the request was made |
| budget | TEXT | e.g. "under $10", "$10–20" |
| mood | TEXT | e.g. "comfort food", "healthy", "quick" |
| portion_pref | TEXT | e.g. "small", "medium" |
| location | TEXT | User-provided area or zip code |
| results | TEXT | JSON blob of returned suggestions |

That's it. No user accounts needed for MVP.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend + backend | Streamlit | Matches stack preference; fast to build single-page apps with minimal boilerplate |
| AI | Claude API (claude-sonnet) | Strong at structured recommendations; easy to prompt for JSON output |
| Database | SQLite | Zero setup, sufficient for one user / demo scale |
| Language | Python | Required per stack preference |

No framework overhead. No auth. No deployment complexity beyond `streamlit run`.

---

## App Views (3 pages)

**Page 1 — Preference Input**
- Sliders/dropdowns: budget range, mood, portion size, location (optional)
- One big "Find me something" button

**Page 2 — Recommendations**
- 3–5 cards returned by Claude, each showing: restaurant name, cuisine type, estimated cost, why it suits solo dining
- "Try again" or "Refine" button

**Page 3 — History (optional / stretch)**
- Shows past searches and what was recommended
- Reads from the SQLite table

---

## Agentic Engineering Plan

The AI layer is a single prompted call — no multi-step agent needed at this scope.

**Prompt structure:**
```
System: You are a solo dining advisor. Return exactly 3-5 restaurant or food suggestions as a JSON array. Each item must include: name, cuisine, estimated_cost, portion_note, why_solo_friendly.

User: Budget: {budget}. Mood: {mood}. Portion preference: {portion_pref}. Location hint: {location}. I am eating alone.
```

**Flow:**

1. User submits form → build prompt from inputs
2. Call Claude API → parse JSON response
3. Render each result as a Streamlit `st.card()` or `st.expander()`
4. Save query + results to SQLite

**Error handling:**
- If Claude returns malformed JSON, retry once with stricter prompt instruction
- If location is empty, omit it from the prompt and note "general suggestions"

---

## Build Plan (~40–50 hours)

| Phase | Tasks | Est. Hours |
|---|---|---|
| Setup | Repo, venv, Streamlit skeleton, SQLite init | 3 |
| Input UI | Preference form, input validation | 6 |
| AI integration | Prompt design, Claude API call, JSON parsing | 10 |
| Results UI | Card rendering, error states | 8 |
| Data persistence | Save/read from SQLite, history view | 6 |
| Polish | Styling, edge cases, empty states | 5 |
| Testing + README | Manual testing, write docs | 5 |
| Buffer | Debugging, prompt tuning | 7 |

---

## Must-Have Feature

User selects "eating alone" + simple preferences → system returns 3–5 suitable restaurant or food suggestions within seconds.