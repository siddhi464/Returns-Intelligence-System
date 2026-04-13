"""
Build Golden Records per SKU for /disposition_insights and profit ticker aggregates.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd

from src.ai_grading import grade_condition, heuristic_grade
from src.data_processing import load_product_frame, merge_data
from src.nrv_engine import calculate_nrv, classify_disposition, nrv_as_pct_msrp
from src.routing_optimizer import clustering_savings, load_warehouses, route_to_hub


def _load_logistics_zip_map(data_dir: str) -> dict[str, dict[str, float]]:
    path = os.path.join(data_dir, "logistics_meta.csv")
    if not os.path.isfile(path):
        return {}

    df = pd.read_csv(path, on_bad_lines="skip")
    out: dict[str, dict[str, float]] = {}

    for _, row in df.iterrows():
        if pd.isna(row.get("zip_code")):
            continue

        z = str(int(float(row["zip_code"])))
        if not z:
            continue

        out[z] = {
            "shipping_rate": float(row.get("shipping_rate", 45) or 45),
            "cluster_density": int(row.get("cluster_density", 0) or 0),
        }

    return out


def _sku_text_bundles(merged: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Aggregate text signals per sku_id for AI + digital twin."""
    bundles: dict[str, dict[str, Any]] = {}

    for sku, g in merged.groupby("sku_id"):
        notes = " ".join(
            g.get("return_note", pd.Series(dtype=str))
            .fillna("")
            .astype(str)
            .tolist()
        )

        transcripts = ""
        if "transcript_agg" in g.columns:
            transcripts = g["transcript_agg"].iloc[0] if len(g) else ""

        review_agg = ""
        if "review_text_agg" in g.columns:
            review_agg = str(g["review_text_agg"].iloc[0]) if len(g) else ""

        dates = g.get("return_date", pd.Series(dtype=str)).astype(str).tolist()

        bundles[str(sku)] = {
            "return_notes": notes[:8000],
            "transcript": str(transcripts)[:8000],
            "review_agg": str(review_agg)[:8000],
            "return_dates": dates,
        }

    return bundles


def build_disposition_insights(
    data_dir: str = "data",
    *,
    stress_wms: bool = False,
    use_llm: bool = True,
) -> dict[str, Any]:

    merged = merge_data(data_dir=data_dir)
    products = load_product_frame(data_dir)
    logistics = _load_logistics_zip_map(data_dir)
    hubs = load_warehouses(data_dir, stress_mode=stress_wms)

    bundles = _sku_text_bundles(merged)

    golden: list[dict[str, Any]] = []
    total_recovered = 0.0
    total_lost = 0.0

    for _, prow in products.iterrows():
        sku_id = str(prow["sku_id"])
        name = str(prow.get("product_name", prow.get("name", sku_id)))
        msrp = float(pd.to_numeric(prow.get("price", 0), errors="coerce") or 0)

        b = bundles.get(
            sku_id,
            {"return_notes": "", "transcript": "", "review_agg": "", "return_dates": []},
        )

        # AI grading
        if use_llm:
            ai = grade_condition(b["return_notes"][:2000], b["transcript"][:2000])
        else:
            ai = heuristic_grade(b["return_notes"], b["transcript"])

        condition = ai["condition_grade"]

        refurb_by_cond = {
            "Faulty": 62.0,
            "Damaged": 28.0,
            "Scrap": 12.0,
            "Open-Box": 18.0,
            "Like-New": 8.0,
            "New": 5.0,
        }
        refurb = float(refurb_by_cond.get(condition, 22.0))

        # logistics lookup
        zip_sample = ""
        sub = merged[merged["sku_id"] == sku_id]

        if len(sub) and "zip_code" in sub.columns:
            z = sub["zip_code"].dropna().astype(int).astype(str)
            if len(z):
                zip_sample = z.mode().iloc[0] if len(z.mode()) else z.iloc[0]

        lm = logistics.get(zip_sample, {"shipping_rate": 45.0, "cluster_density": 0})
        ship = float(lm["shipping_rate"])
        density = int(lm["cluster_density"])
        n_returns = int(len(sub)) if len(sub) else 1

        # NRV
        nrv = calculate_nrv(
            msrp,
            condition,
            shipping=ship,
            inspection=25.0,
            refurbish=refurb,
            storage=12.0,
        )

        # clustering (REAL savings)
        clustered, savings = clustering_savings(
            density,
            n_returns_in_cluster=n_returns,
        )

        # disposition decision
        action, justification, nrv = classify_disposition(
            msrp,
            condition,
            cluster_savings=savings,
            sentiment=ai["sentiment_score"],
        )
        # routing
        route = route_to_hub(
            zip_code=zip_sample or "00000",
            shipping_rate=ship,
            hubs=hubs,
            recommended_action=action,
        )

        route["savings_via_clustering"] = savings if clustered else 0.0
        route["consolidated_collection"] = clustered

        # aggregates
        pct = nrv_as_pct_msrp(nrv, msrp)

        if nrv > 0:
            total_recovered += nrv * max(1, min(n_returns, 50))
        else:
            total_lost += abs(nrv) + (ship + 25 + refurb) * max(1, min(n_returns, 20))

        # FINAL OUTPUT (RESTORED SKU-LEVEL DATA)
        golden.append(
            {
                "sku_id": sku_id,
                "name": name,

                # financials
                "nrv_value": nrv,
                "nrv_pct_msrp": pct,
                "recommended_action": action,

                # routing
                "routing": route,

                # AI summary
                "ai_summary": _ai_summary(
                    condition,
                    ai["key_issues"],
                    route["target_hub"],
                ),
                "condition_grade": condition,
                "sentiment_score": ai["sentiment_score"],
                "key_issues": ai["key_issues"],
                "financial_justification": justification,

                # 🔥 RESTORED DATA FOR SKU TAB
                "return_notes": b["return_notes"],
                "review_agg": b["review_agg"],
                "transcript": b["transcript"],
                "return_dates": b["return_dates"],
                "num_returns": n_returns,
            }
        )

    return {
        "records": golden,
        "profit_recovery": {
            "total_recovered_value": round(total_recovered, 2),
            "total_lost_value": round(total_lost, 2),
        },
        "stress_wms_active": stress_wms,
    }


def _ai_summary(condition: str, issues: list[str], hub: str) -> str:
    iss = ", ".join(issues[:3]) if issues else "No major themes"
    return f"Condition {condition}. Issues: {iss}. Routed toward {hub}."