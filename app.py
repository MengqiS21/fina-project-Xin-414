"""Solo Dining Recommender — Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from db import fetch_recommendation_history, init_db, save_recommendation
from llm import DiningPreferences, LlmError, Recommendation, generate_recommendations

st.set_page_config(page_title="Solo meal planner", layout="wide", page_icon="\U0001f371")

# --- Options (must match validation) ---
BUDGET_OPTIONS = ("", "Under $10", "$10–20", "$20+")
MOOD_OPTIONS = ("", "Comfort food", "Healthy", "Quick", "Adventurous")
PORTION_OPTIONS = ("", "Small", "Medium", "Regular")

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
    s = raw.strip()
    return s if s else None


def _option_index(options: tuple[str, ...], value: str) -> int | None:
    if value in options:
        return options.index(value)
    return None


def _render_recommendation_cards(recs: list[Recommendation]) -> None:
    """One readable block per suggestion with all five fields."""
    for i, r in enumerate(recs, start=1):
        with st.container(border=True):
            st.markdown(f"#### Pick {i}")
            st.markdown(f"**Name:** {r.name}")
            st.markdown(f"**Cuisine:** {r.cuisine}")
            st.markdown(f"**Estimated cost:** {r.estimated_cost}")
            st.markdown(f"**Portion note:** {r.portion_note}")
            st.markdown(f"**Why solo-friendly:** {r.why_solo_friendly}")


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
            save_recommendation(
                budget=prefs.budget,
                mood=prefs.mood,
                portion_pref=prefs.portion_pref,
                location=prefs.location,
                results=new_recs,
            )
            st.rerun()

    if refine:
        st.session_state["last_recommendations"] = []
        st.session_state["_apply_refine_prefill"] = True
        st.session_state["_show_refine_hint"] = True
        st.rerun()


def _render_history_page() -> None:
    """Display persisted recommendations in reverse chronological order."""
    st.divider()
    st.subheader("History")
    history = fetch_recommendation_history()
    if not history:
        st.info("No history yet. Submit your first search on Planner.")
        return

    st.caption(f"{len(history)} saved searches")
    for entry in history:
        location_text = entry["location"] or "General suggestions"
        with st.expander(
            f"{entry['created_at']} — {entry['budget']} / {entry['mood']} / {entry['portion_pref']}",
            expanded=False,
        ):
            if st.button("Use these inputs", key=f"use_history_{entry['id']}"):
                st.session_state["last_preferences"] = DiningPreferences(
                    budget=entry["budget"] or "",
                    mood=entry["mood"] or "",
                    portion_pref=entry["portion_pref"] or "",
                    location=entry["location"],
                )
                st.session_state["last_recommendations"] = []
                st.session_state["_apply_refine_prefill"] = True
                st.session_state["_show_refine_hint"] = True
                st.session_state["view_mode"] = "Planner"
                st.rerun()

            st.markdown(
                f"**Timestamp:** {entry['created_at']}  \n"
                f"**Budget:** {entry['budget']}  \n"
                f"**Mood:** {entry['mood']}  \n"
                f"**Portion:** {entry['portion_pref']}  \n"
                f"**Location:** {location_text}"
            )

            results = entry["results"] if isinstance(entry["results"], list) else []
            if not results:
                st.caption("No parsed recommendation results in this row.")
                continue

            for i, item in enumerate(results, start=1):
                if not isinstance(item, dict):
                    continue
                with st.container(border=True):
                    st.markdown(f"#### Result {i}")
                    st.markdown(f"**Name:** {item.get('name', '-')}")
                    st.markdown(f"**Cuisine:** {item.get('cuisine', '-')}")
                    st.markdown(f"**Estimated cost:** {item.get('estimated_cost', '-')}")
                    st.markdown(f"**Portion note:** {item.get('portion_note', '-')}")
                    st.markdown(
                        f"**Why solo-friendly:** {item.get('why_solo_friendly', '-')}"
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
</style>
        """,
        unsafe_allow_html=True,
    )


init_db()
_inject_theme_css()

st.title("\U0001f371 Solo Dining Recommender")
st.markdown(
    "Pick your **solo meal vibe**—we’ll match you with cozy spots. Fields marked **required** need a choice before we search."
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

with st.form("preferences_form", clear_on_submit=False):
    if st.session_state.pop("_show_refine_hint", False):
        st.info(
            "Adjust your choices in this form, then click **Find me something** again."
        )
    st.caption("Required: budget, mood, and portion. Location is optional.")

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
        )
        st.session_state["last_preferences"] = prefs

        st.markdown("**Submitted values (passed to the AI layer)**")
        st.json(
            {
                "budget": prefs.budget,
                "mood": prefs.mood,
                "portion_pref": prefs.portion_pref,
                "location": prefs.location,
            }
        )

        try:
            recs = generate_recommendations(prefs)
        except LlmError as err:
            st.session_state["last_recommendations"] = []
            st.error(str(err))
        else:
            st.session_state["last_recommendations"] = recs
            save_recommendation(
                budget=prefs.budget,
                mood=prefs.mood,
                portion_pref=prefs.portion_pref,
                location=prefs.location,
                results=recs,
            )
            st.success("Here are tailored suggestions for your solo meal.")

recs = st.session_state.get("last_recommendations") or []
if (
    isinstance(recs, list)
    and recs
    and isinstance(recs[0], Recommendation)
):
    st.divider()
    st.subheader("\U0001f35c Tasty picks for you")
    _render_recommendation_cards(recs)
    _render_results_actions()

if st.session_state.get("last_preferences") and not submitted:
    p = st.session_state["last_preferences"]
    with st.expander("Last submitted preferences (this session)", expanded=False):
        st.json(
            {
                "budget": p.budget,
                "mood": p.mood,
                "portion_pref": p.portion_pref,
                "location": p.location,
            }
        )
