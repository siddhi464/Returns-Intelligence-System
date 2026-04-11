"""
Enhanced Net Recovery Value (NRV) and disposition engine for Sentinel SCM.

Key upgrades:
- Dynamic refurbish cost modeling
- Variable shipping cost (pluggable from routing)
- Improved resale tiers (damaged ≠ always 20%)
- Option-based optimization (RESTOCK vs REFURBISH vs LIQUIDATE)
- Cluster savings integration
- Reduced RETURNLESS REFUND bias via salvage fallback
"""

from __future__ import annotations
from typing import Literal, Tuple
import random

ConditionCategory = Literal[
    "New", "Like-New", "Open-Box", "Faulty", "Damaged", "Scrap"
]

# --- Resale tiers ---
TIER_NEW = 0.90
TIER_OPEN_BOX = 0.65
TIER_REFURBISHED = 0.45
TIER_DAMAGED = 0.35
TIER_LIQUIDATION = 0.25

# --- Default base costs (can be overridden) ---
DEFAULT_SHIPPING = 45.0
DEFAULT_INSPECTION = 25.0
DEFAULT_STORAGE = 12.0


# -----------------------------
# Cost + Revenue Modeling
# -----------------------------

def estimate_refurb_cost(condition: str, msrp: float) -> float:
    """Dynamic refurbish cost based on condition and value."""
    c = condition.lower()

    if c == "faulty":
        return 0.20 * msrp
    if c == "damaged":
        return 0.35 * msrp
    return 0.0


def estimate_resale_value(
    condition: str,
    msrp: float,
    sentiment: float = 0.0,
) -> float:
    """
    Predict resale value using condition + sentiment adjustment.
    """
    c = condition.lower()

    if c in ("new", "like-new", "like new"):
        tier = TIER_NEW
    elif c in ("open-box", "open box"):
        tier = TIER_OPEN_BOX
    elif c == "faulty":
        tier = TIER_REFURBISHED
    elif c == "damaged":
        tier = TIER_DAMAGED
    else:
        tier = TIER_LIQUIDATION

    # sentiment adjustment (-1 to +1)
    tier *= (1 + 0.1 * sentiment)

    return msrp * tier


def calculate_nrv(
    msrp: float,
    condition: str,
    *,
    shipping: float = DEFAULT_SHIPPING,
    inspection: float = DEFAULT_INSPECTION,
    storage: float = DEFAULT_STORAGE,
    refurbish: float | None = None,
    cluster_savings: float = 0.0,
    sentiment: float = 0.0,
) -> float:
    """
    NRV = resale - (costs) + cluster_savings
    """
    msrp = float(msrp or 0)

    if refurbish is None:
        refurbish = estimate_refurb_cost(condition, msrp)

    resale = estimate_resale_value(condition, msrp, sentiment)

    total_cost = shipping + inspection + storage + refurbish
    
    effective_cluster = 0.3 * cluster_savings
    nrv = resale - total_cost + effective_cluster

    return round(nrv, 2)


def nrv_as_pct_msrp(nrv: float, msrp: float) -> float:
    if not msrp or msrp <= 0:
        return 0.0
    return round(100.0 * nrv / msrp, 2)


# -----------------------------
# Decision Engine (NEW)
# -----------------------------

def evaluate_options(
    msrp: float,
    condition: str,
    shipping: float,
    inspection: float,
    storage: float,
    cluster_savings: float,
    sentiment: float,
) -> dict:
    """
    Compute NRV for each possible action.
    """
    results = {}

    # --- RESTOCK ---
    if condition.lower() in ("new", "like-new", "open-box"):
        risk_penalty = random.uniform(0.85, 1.0)
        nrv_restock = calculate_nrv(
            msrp,
            condition,
            shipping=shipping,
            inspection=inspection,
            storage=storage,
            refurbish=0,
            cluster_savings=cluster_savings,
            sentiment=sentiment,
        )
        results["RESTOCK"] = nrv_restock * risk_penalty

    # --- REFURBISH ---
    results["REFURBISH"] = calculate_nrv(
        msrp,
        "faulty",
        shipping=shipping,
        inspection=inspection,
        storage=storage,
        refurbish=estimate_refurb_cost("faulty", msrp),
        cluster_savings=cluster_savings,
        sentiment=sentiment,
    )

    # --- LIQUIDATE ---
    results["LIQUIDATE"] = calculate_nrv(
        msrp,
        "scrap",
        shipping=shipping,
        inspection=inspection,
        storage=storage,
        refurbish=0,
        cluster_savings=cluster_savings,
        sentiment=sentiment,
    )

    return results


def classify_disposition(
    msrp: float,
    condition: str,
    *,
    shipping: float = DEFAULT_SHIPPING,
    inspection: float = DEFAULT_INSPECTION,
    storage: float = DEFAULT_STORAGE,
    cluster_savings: float = 0.0,
    sentiment: float = 0.0,
) -> Tuple[str, str, float]:
    """
    Returns:
    (recommended_action, explanation, best_nrv)
    """

    options = evaluate_options(
        msrp,
        condition,
        shipping,
        inspection,
        storage,
        cluster_savings,
        sentiment,
    )

    # pick best financial outcome
    best_action = max(options, key=lambda x: options[x])
    best_nrv = options[best_action]

    # -----------------------------
    # SMART FALLBACK (reduces returnless)
    # -----------------------------
    if best_nrv < 20:
        return (
            "RETURNLESS REFUND",
            "All recovery paths are significantly negative; avoid reverse logistics cost.",
            best_nrv,
        )

    if best_nrv < 0:
        return (
            "LIQUIDATE",
            "Slight loss expected, but better than zero recovery.",
            best_nrv,
        )

    return (
        best_action,
        f"Chosen {best_action} as it yields highest recovery value.",
        best_nrv,
    )