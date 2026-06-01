# SPEC.md — No More "What Should I Eat?" (Solo Edition)

## Project Overview

A Streamlit-based web app that helps solo diners quickly find suitable dining options based on their personal preferences. Users input their budget, mood, portion preference, and optional location, and the app returns 3–5 AI-generated restaurant or food suggestions tailored for solo dining.

## Developer

**Mengqi Shi**
Agreed Development Fee: **30 GIX Bucks**

## User Stories

1. As a solo diner, I want to input my budget, mood, and portion preference so that I get personalized restaurant suggestions without spending time browsing.
2. As a user, I want to see 3–5 recommendation cards with key details (name, cuisine, estimated cost, why it's solo-friendly) so that I can make a quick decision.
3. As a user, I want a "Try Again" or "Refine" option so that I can get new suggestions if the first results don't appeal to me.
4. As a user, I want my past searches saved so that I can revisit previous recommendations.
5. As a user, I want the app to handle errors gracefully (e.g., malformed AI response, empty location) so that it never crashes or returns blank results.

## Functional Specifications

### Page 1 — Preference Input
- Budget selector: dropdown or slider (e.g., under $10 / $10–20 / $20+)
- Mood selector: dropdown (e.g., comfort food, healthy, quick, adventurous)
- Portion size selector: small / medium / regular
- Location input: optional free-text field (zip code or neighborhood)
- "Find me something" submit button

### Page 2 — Recommendations
- Display 3–5 cards, each containing:
  - Restaurant/food name
  - Cuisine type
  - Estimated cost
  - Portion note
  - Why it's solo-friendly
- "Try Again" button to re-run with same inputs
- "Refine" button to go back to Page 1

### Page 3 — History (Stretch Goal)
- List of past queries with timestamps
- Each entry shows inputs used and recommendations returned
- Reads from SQLite database

## Acceptance Criteria

| Feature | Acceptance Criteria |
|---|---|
| Input form | All 3 required fields (budget, mood, portion) must be selectable before submission |
| AI response | Returns valid JSON with 3–5 items within 10 seconds |
| Cards | Each card displays all 5 required fields |
| Error handling | If AI returns malformed JSON, app retries once and shows a user-friendly error if retry fails |
| Empty location | App works without location; prompt omits location and notes "general suggestions" |
| Data persistence | Each query + result is saved to SQLite |
| History view | Past searches are retrievable and displayed in reverse chronological order |

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend + Backend | Python + Streamlit |
| AI | Claude API (claude-sonnet) |
| Database | SQLite |
| Language | Python |

## Out of Scope (MVP)

- User authentication / accounts
- Real-time restaurant availability or external API integration (e.g., Yelp, Google Maps)
- Mobile app
- Multi-user support
