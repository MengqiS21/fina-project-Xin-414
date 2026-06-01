"""Solo Dining Recommender — Streamlit entrypoint."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db import fetch_recommendation_history, init_db, save_recommendation, update_rating
from llm import DiningPreferences, LlmError, Recommendation, generate_recommendations

st.set_page_config(page_title="Solo meal planner", layout="wide", page_icon="\U0001f371")

# --- Options (must match validation) ---
BUDGET_OPTIONS = ("", "Under $10", "$10–20", "$20+")
MOOD_OPTIONS = ("", "Comfort food", "Healthy", "Quick", "Adventurous")
PORTION_OPTIONS = ("", "Small", "Medium", "Regular")
DIETARY_OPTIONS = ("Vegetarian", "Vegan", "Gluten-free", "Nut-free", "Dairy-free", "Halal", "Kosher")

_PLACEHOLDER = {
    "budget": "Select budget…",
    "mood": "Select mood…",
    "portion": "Select portion size…",
}


def _fmt_select(label_key: str, value: str) -> str:
    if value == "":
        return _PLACEHOLDER[label_key]
    return value


def _validate_required(budget: str, mood: str, portion: str) -> list[str]:
    errors: list[str] = []
    if budget == "":
        errors.append("Budget is required.")
    if mood == "":
        errors.append("Mood is required.")
    if portion == "":
        errors.append("Portion size is required.")
    return errors


def _normalize_location(raw: str) -> str | None:
    s = raw.strip()[:120]
    return s if s else None


def _option_index(options: tuple[str, ...], value: str) -> int | None:
    if value in options:
        return options.index(value)
    return None


def _render_pick_card(
    index: int,
    *,
    name: str,
    cuisine: str,
    estimated_cost: str,
    portion_note: str,
    why_solo_friendly: str,
    address: str = "",
) -> None:
    """One bordered recommendation card (Planner results and History)."""
    with st.container(border=True):
        st.markdown(f"#### Pick {index}")
        st.markdown(f"**Name:** {name}")
        st.markdown(f"**Cuisine:** {cuisine}")
        st.markdown(f"**Estimated cost:** {estimated_cost}")
        st.markdown(f"**Portion note:** {portion_note}")
        st.markdown(f"**Why solo-friendly:** {why_solo_friendly}")
        if address:
            st.caption(f"📍 {address}")


def _render_recommendation_cards(recs: list[Recommendation]) -> None:
    for i, r in enumerate(recs, start=1):
        _render_pick_card(
            i,
            name=r.name,
            cuisine=r.cuisine,
            estimated_cost=r.estimated_cost,
            portion_note=r.portion_note,
            why_solo_friendly=r.why_solo_friendly,
            address=r.address,
        )


def _format_history_timestamp(raw: str) -> str:
    """Show a readable label in History expanders."""
    text = (raw or "").strip()
    if not text:
        return "Unknown time"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except ValueError:
        return text


def _history_summary(entry: dict) -> str:
    when = _format_history_timestamp(str(entry.get("created_at", "")))
    budget = entry.get("budget") or "Any budget"
    mood = entry.get("mood") or "Any mood"
    portion = entry.get("portion_pref") or "Any portion"
    return f"{when} | {budget} / {mood} / {portion}"


def _render_rating_section() -> None:
    """Thumbs-up / thumbs-down feedback for the current recommendation set."""
    row_id = st.session_state.get("last_recommendation_id")
    if not row_id:
        return
    rating_key = f"rating_{row_id}"
    current = st.session_state.get(rating_key)
    st.markdown("**Was this helpful?**")
    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("👍", key=f"up_{row_id}", disabled=(current == 1)):
            update_rating(row_id, 1)
            st.session_state[rating_key] = 1
            st.rerun()
    with c2:
        if st.button("👎", key=f"down_{row_id}", disabled=(current == -1)):
            update_rating(row_id, -1)
            st.session_state[rating_key] = -1
            st.rerun()
    if current == 1:
        st.caption("Thanks for the feedback! 👍")
    elif current == -1:
        st.caption("Thanks for the feedback! Try adjusting your preferences. 👎")


def _render_results_actions() -> None:
    """Try Again (same prefs) and Refine (back to form / clear results)."""
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        try_again = st.button(
            "Try Again",
            use_container_width=True,
            help="Get a new set of suggestions using your last submitted preferences.",
            key="results_try_again",
        )
    with c2:
        refine = st.button(
            "Refine",
            use_container_width=True,
            help="Clear results and adjust your preferences above.",
            key="results_refine",
        )

    prefs = st.session_state.get("last_preferences")
    if try_again and prefs:
        try:
            with st.spinner("Getting fresh suggestions…"):
                new_recs = generate_recommendations(prefs)
        except LlmError as err:
            st.error(str(err))
        else:
            st.session_state["last_recommendations"] = new_recs
            row_id = save_recommendation(
                budget=prefs.budget,
                mood=prefs.mood,
                portion_pref=prefs.portion_pref,
                location=prefs.location,
                results=new_recs,
                dietary_restrictions=prefs.dietary_restrictions,
            )
            st.session_state["last_recommendation_id"] = row_id
            st.rerun()

    if refine:
        st.session_state["last_recommendations"] = []
        st.session_state["_apply_refine_prefill"] = True
        st.session_state["_show_refine_hint"] = True
        st.rerun()


def _render_history_charts(history: list[dict]) -> None:
    """Bar charts showing mood and budget distribution across all searches."""
    if len(history) < 2:
        return
    from collections import Counter
    import pandas as pd

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Mood breakdown")
        mood_counts = Counter(e["mood"] for e in history if e.get("mood"))
        if mood_counts:
            st.bar_chart(pd.Series(mood_counts))
    with col2:
        st.caption("Budget breakdown")
        budget_counts = Counter(e["budget"] for e in history if e.get("budget"))
        if budget_counts:
            st.bar_chart(pd.Series(budget_counts))


def _render_history_page() -> None:
    """Display persisted recommendations in reverse chronological order."""
    st.divider()
    st.subheader("\U0001f4dc Your history")
    history = fetch_recommendation_history()
    if not history:
        st.info("No history yet. Submit your first search on **Planner**.")
        return

    st.caption(f"{len(history)} saved search{'es' if len(history) != 1 else ''}")
    _render_history_charts(history)
    st.divider()

    for entry in history:
        location_text = entry["location"] or "General suggestions"
        rating = entry.get("rating")
        rating_badge = " 👍" if rating == 1 else (" 👎" if rating == -1 else "")
        with st.expander(_history_summary(entry) + rating_badge, expanded=False):
            if st.button(
                "Use these inputs",
                key=f"use_history_{entry['id']}",
                use_container_width=True,
                help="Prefill the Planner form with this search.",
            ):
                dr = entry.get("dietary_restrictions") or []
                st.session_state["last_preferences"] = DiningPreferences(
                    budget=entry["budget"] or "",
                    mood=entry["mood"] or "",
                    portion_pref=entry["portion_pref"] or "",
                    location=entry["location"],
                    dietary_restrictions=tuple(dr),
                )
                st.session_state["last_recommendations"] = []
                st.session_state["_apply_refine_prefill"] = True
                st.session_state["_show_refine_hint"] = True
                st.session_state["view_mode"] = "Planner"
                st.rerun()

            dr_list = entry.get("dietary_restrictions") or []
            dr_text = ", ".join(dr_list) if dr_list else "None"
            st.markdown(
                f"**When:** {_format_history_timestamp(str(entry['created_at']))}  \n"
                f"**Budget:** {entry['budget'] or '-'}  \n"
                f"**Mood:** {entry['mood'] or '-'}  \n"
                f"**Portion:** {entry['portion_pref'] or '-'}  \n"
                f"**Dietary:** {dr_text}  \n"
                f"**Location:** {location_text}"
            )

            results = entry["results"] if isinstance(entry["results"], list) else []
            if not results:
                st.caption("No saved recommendations for this search.")
                continue

            for i, item in enumerate(results, start=1):
                if not isinstance(item, dict):
                    continue
                _render_pick_card(
                    i,
                    name=str(item.get("name") or "-"),
                    cuisine=str(item.get("cuisine") or "-"),
                    estimated_cost=str(item.get("estimated_cost") or "-"),
                    portion_note=str(item.get("portion_note") or "-"),
                    why_solo_friendly=str(item.get("why_solo_friendly") or "-"),
                    address=str(item.get("address") or ""),
                )


def _inject_theme_css() -> None:
    """Warm, playful meal-planner look + focus visibility and tap targets."""
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --meal-page: #faf8f4;
    --meal-page-2: #f7f5f0;
    --meal-strawberry: #c43d5c;
    --meal-text: #2c241c;
    --meal-muted: #5a4d42;
    --meal-border: #e8ddd4;
    --meal-card-edge: #e0cfc4;
    --meal-card-bg: #fffefb;
  }
  html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: "Nunito", "Segoe UI", system-ui, sans-serif !important;
    color: var(--meal-text);
  }
  .stApp {
    /* Near-white warm beige — very subtle depth, stays easy to read */
    background: linear-gradient(180deg, #fcfcfa 0%, var(--meal-page) 35%, var(--meal-page-2) 100%) !important;
  }
  [data-testid="stHeader"] {
    background: rgba(252, 252, 250, 0.92);
    backdrop-filter: blur(8px);
  }
  .block-container {
    padding-top: 1rem;
  }
  h1, h2, h3 {
    color: var(--meal-strawberry) !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
  }
  p, span, label, li {
    color: var(--meal-text);
  }
  .stCaption, [data-testid="stCaption"] {
    color: var(--meal-muted) !important;
  }
  hr {
    border: none !important;
    height: 3px !important;
    margin: 1.25rem 0 !important;
    border-radius: 3px !important;
    background: linear-gradient(90deg, transparent, #f0d4dc, #edd9c0, transparent) !important;
    opacity: 0.85;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 22px !important;
    border: 1px solid var(--meal-card-edge) !important;
    background: var(--meal-card-bg) !important;
    box-shadow: 0 2px 14px rgba(44, 36, 28, 0.07) !important;
    padding: 0.35rem 0.6rem !important;
  }
  /* Stronger body copy contrast on the light page */
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li,
  [data-testid="stMarkdownContainer"] span {
    color: var(--meal-text) !important;
  }
  [data-testid="stMarkdownContainer"] strong {
    color: #241c18 !important;
  }
  /* Widget labels + helper text */
  label[data-testid="stWidgetLabel"] p,
  label[data-testid="stWidgetLabel"] span {
    color: var(--meal-text) !important;
    font-weight: 600 !important;
  }
  div[data-testid="stWidgetLabel"] p {
    color: var(--meal-text) !important;
    font-weight: 600 !important;
  }
  small, [data-testid="stCaption"] {
    color: var(--meal-muted) !important;
  }
  div[data-testid="stFormSubmitButton"] button {
    min-height: 48px !important;
    border-radius: 9999px !important;
    background: linear-gradient(135deg, #ff8fab 0%, #ffb088 55%, #ffc96b 100%) !important;
    color: #3d2a26 !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 4px 16px rgba(255, 120, 140, 0.35) !important;
  }
  div[data-testid="stFormSubmitButton"] button:hover {
    box-shadow: 0 6px 22px rgba(255, 120, 140, 0.45) !important;
    filter: brightness(1.03);
  }
  div[data-testid="column"] button[kind="secondary"],
  div[data-testid="column"] button[kind="primary"] {
    min-height: 48px !important;
    border-radius: 9999px !important;
    font-weight: 700 !important;
  }
  div[data-testid="column"] button[kind="secondary"] {
    background: #ffffff !important;
    color: var(--meal-text) !important;
    border: 2px solid #dccfc4 !important;
  }
  div[data-testid="column"] button[kind="primary"] {
    background: linear-gradient(135deg, #ff8fab, #ffa981) !important;
    color: #3d2a26 !important;
    border: none !important;
  }
  [data-testid="stExpander"] button[kind="secondary"],
  [data-testid="stExpander"] button[kind="primary"] {
    min-height: 44px !important;
    border-radius: 9999px !important;
    font-weight: 700 !important;
    background: #ffffff !important;
    color: var(--meal-text) !important;
    border: 2px solid #dccfc4 !important;
  }
  [data-testid="stRadio"] label {
    font-weight: 700 !important;
    color: var(--meal-text) !important;
  }
  [data-testid="stRadio"] [data-baseweb="radio"] {
    gap: 0.75rem !important;
  }
  div[data-baseweb="select"] > div,
  div[data-baseweb="input"] > div {
    border-radius: 14px !important;
    background-color: #ffffff !important;
    border-color: #d4c9bf !important;
  }
  /* JSON / code blocks stay readable on beige */
  [data-testid="stJson"] {
    background: #ffffff !important;
    border: 1px solid var(--meal-border) !important;
    border-radius: 12px !important;
  }
  .block-container button:focus-visible,
  .block-container [role="button"]:focus-visible,
  .block-container input:focus-visible,
  .block-container textarea:focus-visible,
  .block-container [tabindex]:focus-visible {
    outline: 3px solid #c94f6e !important;
    outline-offset: 2px !important;
  }
  [data-testid="stSuccess"] {
    background: linear-gradient(90deg, #e8f8ef, #f0fff8) !important;
    border: 1px solid #b8e6c8 !important;
    border-radius: 16px !important;
  }
  [data-testid="stInfo"] {
    background: linear-gradient(90deg, #fff5f8, #fff9fb) !important;
    border: 1px solid var(--meal-border) !important;
    border-radius: 16px !important;
  }
  [data-testid="stAlert"] {
    border-radius: 14px !important;
  }
  [data-testid="stError"] {
    border-radius: 14px !important;
  }
  [data-testid="stSpinner"] {
    color: var(--meal-strawberry) !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


init_db()
_inject_theme_css()

st.title("\U0001f371 Solo Dining Recommender")
st.markdown(
    "Pick your **solo meal vibe** and we will match you with cozy spots. "
    "Fields marked **required** need a choice before we search."
)

page = st.radio(
    "View",
    options=("Planner", "History"),
    horizontal=True,
    label_visibility="collapsed",
    key="view_mode",
)
if page == "History":
    _render_history_page()
    st.stop()

st.divider()
st.subheader("\u2728 Your preferences")

_prefill = st.session_state.pop("_apply_refine_prefill", False)
_lp = st.session_state.get("last_preferences") if _prefill else None

_budget_idx = _option_index(BUDGET_OPTIONS, _lp.budget) if _lp else None
_mood_idx = _option_index(MOOD_OPTIONS, _lp.mood) if _lp else None
_portion_idx = _option_index(PORTION_OPTIONS, _lp.portion_pref) if _lp else None
_location_default = (_lp.location or "") if _lp else ""
_dietary_default = list(_lp.dietary_restrictions) if _lp else []

with st.form("preferences_form", clear_on_submit=False):
    if st.session_state.pop("_show_refine_hint", False):
        st.info(
            "Adjust your choices in this form, then click **Find me something** again."
        )
    st.caption("Required: budget, mood, and portion. Location and dietary filters are optional.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        budget_kw: dict = {
            "label": "Budget (required)",
            "options": BUDGET_OPTIONS,
            "format_func": lambda x: _fmt_select("budget", x),
            "help": "Price range for your meal.",
            "label_visibility": "visible",
        }
        if _budget_idx is not None:
            budget_kw["index"] = _budget_idx
        budget = st.selectbox(**budget_kw)
    with c2:
        mood_kw: dict = {
            "label": "Mood (required)",
            "options": MOOD_OPTIONS,
            "format_func": lambda x: _fmt_select("mood", x),
            "help": "What kind of meal experience you want.",
            "label_visibility": "visible",
        }
        if _mood_idx is not None:
            mood_kw["index"] = _mood_idx
        mood = st.selectbox(**mood_kw)

    portion_kw: dict = {
        "label": "Portion size (required)",
        "options": PORTION_OPTIONS,
        "format_func": lambda x: _fmt_select("portion", x),
        "help": "How much food you want.",
        "label_visibility": "visible",
    }
    if _portion_idx is not None:
        portion_kw["index"] = _portion_idx
    portion = st.selectbox(**portion_kw)

    dietary = st.multiselect(
        "Dietary restrictions (optional)",
        options=DIETARY_OPTIONS,
        default=_dietary_default,
        help="Select any dietary restrictions or allergies. All suggestions will respect these.",
        label_visibility="visible",
    )

    _loc_kw: dict = {
        "label": "Location (optional)",
        "max_chars": 120,
        "placeholder": "e.g. Capitol Hill, downtown, or 98105",
        "help": "Neighborhood, landmark, or ZIP. Leave blank for general suggestions.",
        "label_visibility": "visible",
        "autocomplete": "street-address",
    }
    if _prefill:
        _loc_kw["value"] = _location_default
    location_raw = st.text_input(**_loc_kw)

    submitted = st.form_submit_button(
        "Find me something",
        type="primary",
        use_container_width=True,
        help="Submit when budget, mood, and portion are filled in.",
    )

if submitted:
    errs = _validate_required(budget, mood, portion)
    loc = _normalize_location(location_raw)

    if errs:
        for msg in errs:
            st.error(msg, icon="⚠️")
    else:
        prefs = DiningPreferences(
            budget=budget,
            mood=mood,
            portion_pref=portion,
            location=loc,
            dietary_restrictions=tuple(dietary),
        )
        st.session_state["last_preferences"] = prefs

        try:
            with st.spinner("Finding tasty spots for you…"):
                recs = generate_recommendations(prefs)
        except LlmError as err:
            st.session_state["last_recommendations"] = []
            st.error(str(err))
        else:
            st.session_state["last_recommendations"] = recs
            row_id = save_recommendation(
                budget=prefs.budget,
                mood=prefs.mood,
                portion_pref=prefs.portion_pref,
                location=prefs.location,
                results=recs,
                dietary_restrictions=prefs.dietary_restrictions,
            )
            st.session_state["last_recommendation_id"] = row_id
            st.success("Here are tailored suggestions for your solo meal.")

recs = st.session_state.get("last_recommendations") or []
if (
    isinstance(recs, list)
    and recs
    and isinstance(recs[0], Recommendation)
):
    st.divider()
    st.subheader("\U0001f35c Tasty picks for you")
    st.caption(
        "⚠️ Suggestions are AI-generated. Restaurant details may vary — always verify before visiting."
    )
    _render_recommendation_cards(recs)
    st.divider()
    _render_rating_section()
    _render_results_actions()
