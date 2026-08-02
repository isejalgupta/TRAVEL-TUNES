"""
AI activity generator for TripTunes.

The app ships with hand-seeded activities for a few cities. This module
lets ANY city work: if the database has no activities for a place the
user typed, we ask the LLM to generate a realistic list, validate it,
and cache it into the database - so the same city is instant next time
and flows straight into the budget/schedule optimisers.

This is generative-AI integration as a *data source*: the model fills
the same Activity table the seeded data uses, so every existing endpoint
and tool keeps working unchanged.

Honesty note: generated costs/ratings/durations are plausible estimates,
not verified facts - the same caveat as the route cost estimate.
"""

import json
import re

from sqlalchemy.orm import Session

from database import Activity as ActivityRow
import llm  # from ChatBot/, resolved via the sys.path setup in app.py

# Categories we constrain the model to, so the UI/filters stay tidy.
CATEGORIES = ["History", "Nature", "Food", "Shopping", "Spiritual",
              "Adventure", "Sightseeing", "Culture", "Entertainment", "Nightlife"]

GENERATE_COUNT = 8


class ActivityGenError(RuntimeError):
    """Generation failed (AI not configured, or unusable response)."""


def _prompt(city: str, count: int) -> str:
    return (
        f"You are a travel expert. List {count} real, well-known tourist "
        f"activities or attractions in {city}.\n"
        f"Return ONLY a JSON array (no prose, no code fences). Each element:\n"
        f'  "name": string (the attraction),\n'
        f'  "category": one of {CATEGORIES},\n'
        f'  "cost": integer, typical entry fee in Indian rupees (0 if free),\n'
        f'  "rating": number 1-5 (one decimal),\n'
        f'  "duration": number, typical hours to visit (e.g. 1.5).\n'
        f"Use real places in {city}. Example element: "
        f'{{"name":"Example Fort","category":"History","cost":50,'
        f'"rating":4.6,"duration":2}}'
    )


def _extract_json_array(text: str) -> list:
    """Pull a JSON array out of the model's reply, tolerating code fences
    or stray prose around it."""
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # Grab the outermost [ ... ].
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ActivityGenError("Model did not return a JSON array.")
    return json.loads(text[start:end + 1])


def _clean_item(raw: dict) -> dict | None:
    """Validate/coerce one generated activity; return None to drop it.

    Requires a name plus all three numeric fields to actually be present -
    an item missing cost/rating/duration is treated as junk and dropped,
    rather than silently filled with defaults.
    """
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "")).strip()
    if not name or any(k not in raw for k in ("cost", "rating", "duration")):
        return None
    try:
        cost = max(0.0, float(raw["cost"]))
        rating = min(5.0, max(0.0, float(raw["rating"])))
        duration = float(raw["duration"])
    except (ValueError, TypeError):
        return None
    if duration <= 0:
        duration = 1.0
    category = str(raw.get("category", "Sightseeing")).strip().title()
    if category not in CATEGORIES:
        category = "Sightseeing"
    return {"name": name, "category": category, "cost": cost,
            "rating": round(rating, 1), "duration": duration}


def generate_activities(city: str, count: int = GENERATE_COUNT) -> list[dict]:
    """Ask the LLM for a validated list of activities for a city.

    Raises ActivityGenError if the AI isn't configured or the response
    can't be parsed into at least one usable activity.
    """
    try:
        model = llm.build_llm(temperature=0.4)
    except llm.LLMNotConfigured as exc:
        raise ActivityGenError(str(exc)) from exc

    try:
        reply = model.invoke(_prompt(city, count))
        content = reply.content
    except Exception as exc:
        raise ActivityGenError(f"AI request failed: {exc}") from exc

    # Some providers return content as a list of parts.
    if isinstance(content, list):
        content = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )

    items = [c for c in (_clean_item(r) for r in _extract_json_array(content)) if c]
    if not items:
        raise ActivityGenError(f"No usable activities generated for {city}.")
    return items


def ensure_city(db: Session, city: str) -> list:
    """Return the DB activity rows for a city, generating + caching them
    with the LLM if none exist yet. Case-insensitive lookup.

    Raises ActivityGenError if generation is needed but fails.
    """
    city = (city or "").strip()
    if not city:
        return []

    rows = db.query(ActivityRow).filter(ActivityRow.location.ilike(city)).all()
    if rows:
        return rows

    generated = generate_activities(city)          # may raise ActivityGenError
    canonical = city.title()
    for it in generated:
        db.add(ActivityRow(
            name=it["name"], location=canonical, category=it["category"],
            cost=it["cost"], rating=it["rating"], duration=it["duration"],
        ))
    db.commit()
    return db.query(ActivityRow).filter(ActivityRow.location.ilike(city)).all()
