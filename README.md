# No More "What Should I Eat?" (Solo Edition)

A Streamlit web app that helps solo diners make quick, confident dining decisions. Input your budget, mood, and portion preference — get 3–5 personalized restaurant or food suggestions in seconds.

**Live app:** https://fina-project-xin-414.streamlit.app

## Problem

People who eat alone — especially students and young professionals — often struggle to decide what to eat. Existing food apps are designed for groups or prioritize popularity, leading to oversized portions, high costs, or uncomfortable environments for solo diners.

## Solution

A lightweight, AI-powered tool that returns curated, solo-friendly dining suggestions based on your personal preferences. No accounts. No browsing. Just answers.

## Features

- Preference input: budget, mood, portion size, optional location
- AI-generated recommendations (3–5 cards per query)
- "Try Again" and "Refine" options
- Query history saved to SQLite, viewable in reverse chronological order
- Graceful error handling with automatic retry on malformed AI responses

## Tech Stack

Python · Streamlit · Claude API · SQLite

## Developer

**Mengqi Shi** — Development fee: 30 GIX Bucks

## Timeline & Check-in Points

| Milestone | Target Date | Required Progress |
|---|---|---|
| ✅ Check-in 1: Architecture | Apr 13, 2026 | ARCHITECTURE.md committed; repo structure set up; Streamlit skeleton running locally |
| ✅ Check-in 2: Core Feature | Apr 27, 2026 | Preference input form complete; Claude API integrated; recommendation cards rendering with real data |
| ✅ Check-in 3: Full MVP | May 18, 2026 | Error handling complete; SQLite persistence working; history view functional; all core issues closed |
| 🔲 Final Delivery | Jun 1, 2026 | App fully polished and demo-ready; all issues closed; README finalized |

## Getting Started

Try it live at https://fina-project-xin-414.streamlit.app — no install needed.

To run locally:
```bash
pip install streamlit anthropic python-dotenv
cp .env.example .env   # add your ANTHROPIC_API_KEY
streamlit run app.py
```

## Project Structure
```
├── app.py           # Main Streamlit app
├── db.py            # SQLite helpers
├── llm.py           # Claude API integration
├── data/            # SQLite database (auto-created)
├── SPEC.md          # Project specification
├── ARCHITECTURE.md  # Developer architecture doc
└── README.md
```
