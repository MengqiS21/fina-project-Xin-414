"""Claude API integration for solo dining recommendations."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Optional: override default model (see Anthropic model IDs in dashboard docs).
DEFAULT_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a solo dining advisor. Respond with a single JSON array only—no markdown code fences, no text before or after the array.

The array must contain between 3 and 5 objects (inclusive). Each object must be a JSON object with exactly these string fields:
- name
- cuisine
- estimated_cost
- portion_note
- why_solo_friendly

Use realistic restaurant or food-spot suggestions. All field values must be non-empty strings."""

RETRY_USER_SUFFIX = """

CRITICAL: Your previous reply was not usable because it was not valid JSON or did not match the required shape. Reply again with ONLY a JSON array (characters [ ... ]), containing 3 to 5 objects. Each object must include exactly these keys: "name", "cuisine", "estimated_cost", "portion_note", "why_solo_friendly". No markdown, no commentary."""


@dataclass(frozen=True)
class DiningPreferences:
    """User preferences passed from the form to the AI layer."""

    budget: str
    mood: str
    portion_pref: str
    location: str | None = None


@dataclass(frozen=True)
class Recommendation:
    """One structured suggestion from the model."""

    name: str
    cuisine: str
    estimated_cost: str
    portion_note: str
    why_solo_friendly: str


class LlmError(Exception):
    """Configuration, API, or parsing failure for the recommendation flow."""


_REQUIRED_KEYS = frozenset(
    {"name", "cuisine", "estimated_cost", "portion_note", "why_solo_friendly"}
)


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise LlmError(
            "Missing ANTHROPIC_API_KEY. Set it in your environment or in a .env file "
            "(see project README)."
        )
    return key


def _build_user_prompt(prefs: DiningPreferences) -> str:
    parts = [
        f"Budget: {prefs.budget}.",
        f"Mood: {prefs.mood}.",
        f"Portion preference: {prefs.portion_pref}.",
    ]
    if prefs.location:
        parts.append(f"Location hint: {prefs.location}.")
    else:
        parts.append(
            "Location: not specified—offer general suggestions not tied to a specific neighborhood."
        )
    parts.append("I am eating alone.")
    return " ".join(parts)


def _extract_json_text(raw: str) -> str:
    """Strip optional markdown fences; otherwise return stripped text."""
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return m.group(1).strip()
    return text


def _coerce_items(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, list):
        raise ValueError("JSON root must be an array")
    n = len(data)
    if not (3 <= n <= 5):
        raise ValueError(f"Expected 3–5 items, got {n}")
    out: list[dict[str, str]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not an object")
        missing = _REQUIRED_KEYS - set(item.keys())
        if missing:
            raise ValueError(f"Item {i} missing keys: {sorted(missing)}")
        row = {k: str(item[k]).strip() for k in _REQUIRED_KEYS}
        if any(not row[k] for k in row):
            raise ValueError(f"Item {i} has empty required fields")
        out.append(row)
    return out


def _parse_response_to_recommendations(text: str) -> list[Recommendation]:
    payload = _extract_json_text(text)
    data = json.loads(payload)
    rows = _coerce_items(data)
    return [
        Recommendation(
            name=r["name"],
            cuisine=r["cuisine"],
            estimated_cost=r["estimated_cost"],
            portion_note=r["portion_note"],
            why_solo_friendly=r["why_solo_friendly"],
        )
        for r in rows
    ]


def _call_claude(system: str, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=_get_api_key())
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # noqa: BLE001 — surface API errors to UI
        raise LlmError(f"Claude API request failed: {exc}") from exc

    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            parts.append(block.text)
    if not parts:
        raise LlmError("Claude returned no text content.")
    return "".join(parts)


def generate_recommendations(prefs: DiningPreferences) -> list[Recommendation]:
    """
    Call Claude with structured prompts and return validated recommendations.

    On malformed JSON or invalid shape, retries once with a stricter instruction.
    """
    _get_api_key()  # fail fast before network
    user = _build_user_prompt(prefs)

    first = _call_claude(SYSTEM_PROMPT, user)
    try:
        return _parse_response_to_recommendations(first)
    except (json.JSONDecodeError, ValueError) as first_err:
        retry_user = user + RETRY_USER_SUFFIX
        second = _call_claude(SYSTEM_PROMPT, retry_user)
        try:
            return _parse_response_to_recommendations(second)
        except (json.JSONDecodeError, ValueError) as second_err:
            raise LlmError(
                "Could not parse a valid JSON array with 3–5 items after one retry. "
                f"First error: {first_err!s}. Retry error: {second_err!s}"
            ) from second_err
