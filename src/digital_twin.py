"""
Durability Digital Twin: physical entities, failure modes, health index 0–100,
and 3D heatmap coordinates for generic furniture visualization.
HealthScore = 100 - min(100, sum(event_weight * weight) * decay_factor)
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

# Weights per spec
W_WARRANTY = 5.0
W_RETURN_BROKEN = 3.0
W_REVIEW_LIGHT = 1.0

# Keywords
BROKEN_PAT = re.compile(r"\b(broken|snapped|snap|cracked|shattered|structural)\b", re.I)
WOBBLE_PAT = re.compile(r"\b(wobble|wobbly|finish|scratch|scuff|blemish)\b", re.I)
ENTITY_PAT = re.compile(
    r"\b(leg|legs|hinge|hinges|drawer|top|surface|frame|joint|door|shelf|hardware|base)\b",
    re.I,
)


def _days_ago(date_str: str | None) -> float | None:
    if not date_str or not str(date_str).strip():
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return (datetime.now() - d).days
        except ValueError:
            continue
    return None


def _decay_for_days(days: float | None) -> float:
    if days is None:
        return 1.0
    return 2.0 if days <= 7 else 1.0


def extract_entities_and_failures(text: str) -> tuple[list[str], list[str]]:
    t = text or ""
    entities = list({m.group(1).lower() for m in ENTITY_PAT.finditer(t)})
    failures: list[str] = []
    if BROKEN_PAT.search(t):
        failures.append("structural_failure")
    if WOBBLE_PAT.search(t) and "structural_failure" not in failures:
        failures.append("cosmetic_or_stability")
    return entities, failures


def component_to_heatmap_xyz(component: str) -> list[float]:
    """Generic furniture rig: normalized positions for Three.js overlay."""
    c = (component or "center").lower()
    presets: dict[str, list[float]] = {
        "leg": [0.35, 0.08, 0.4],
        "legs": [0.35, 0.08, 0.4],
        "hinge": [0.5, 0.55, 0.12],
        "hinges": [0.5, 0.55, 0.12],
        "drawer": [0.2, 0.35, 0.5],
        "top": [0.5, 0.72, 0.5],
        "surface": [0.5, 0.72, 0.5],
        "frame": [0.5, 0.45, 0.5],
        "joint": [0.38, 0.15, 0.42],
        "door": [0.82, 0.5, 0.5],
        "shelf": [0.5, 0.5, 0.25],
        "hardware": [0.6, 0.4, 0.15],
        "base": [0.5, 0.05, 0.5],
    }
    for key, xyz in presets.items():
        if key in c:
            return xyz
    return [0.5, 0.5, 0.5]


def compute_health_index(
    *,
    warranty_events: int = 0,
    return_notes_text: str = "",
    review_texts: list[str] | None = None,
    contact_transcripts: str = "",
    event_dates: list[str | None] | None = None,
) -> dict[str, Any]:
    """
    Aggregate weighted events with decay for last 7 days (2x).
    """
    review_texts = review_texts or []
    event_dates = event_dates or []
    total_weighted = 0.0

    def add_event(w: float, text: str, date_str: str | None = None):
        nonlocal total_weighted
        days = _days_ago(date_str)
        decay = _decay_for_days(days)
        total_weighted += w * decay

    for _ in range(int(warranty_events)):
        add_event(W_WARRANTY, "warranty", None)

    combined_returns = return_notes_text or ""
    if combined_returns:
        _, fails = extract_entities_and_failures(combined_returns)
        if fails and "structural_failure" in fails:
            add_event(W_RETURN_BROKEN, combined_returns, event_dates[0] if event_dates else None)

    for i, rt in enumerate(review_texts):
        if BROKEN_PAT.search(rt):
            add_event(W_RETURN_BROKEN, rt, event_dates[i] if i < len(event_dates) else None)
        elif WOBBLE_PAT.search(rt):
            ds = event_dates[i] if i < len(event_dates) else None
            add_event(W_REVIEW_LIGHT, rt, ds)

    if contact_transcripts:
        if BROKEN_PAT.search(contact_transcripts):
            add_event(W_RETURN_BROKEN, contact_transcripts, None)
        elif WOBBLE_PAT.search(contact_transcripts):
            add_event(W_REVIEW_LIGHT, contact_transcripts, None)

    penalty = min(100.0, total_weighted * 8.0)  # scale so multiple signals matter
    health = max(0.0, min(100.0, 100.0 - penalty))

    all_text = " ".join([combined_returns, contact_transcripts, " ".join(review_texts)])
    entities, failures = extract_entities_and_failures(all_text)
    top_component = entities[0] if entities else "assembly"

    heatmap_points: list[dict[str, Any]] = []
    for e in entities[:5]:
        xyz = component_to_heatmap_xyz(e)
        heatmap_points.append({"component": e, "intensity": 0.85, "position": xyz})

    if not heatmap_points:
        heatmap_points.append(
            {"component": top_component, "intensity": 0.4, "position": component_to_heatmap_xyz(top_component)}
        )

    return {
        "health_index": round(health, 1),
        "top_failure_component": top_component.title(),
        "physical_entities": list(dict.fromkeys(entities))[:10],
        "failure_modes": list(dict.fromkeys(failures)),
        "heatmap_coordinates": heatmap_points,
    }
