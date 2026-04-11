from __future__ import annotations
import pandas as pd


def generate_smart_alerts(df: pd.DataFrame, sku_df: pd.DataFrame | None = None) -> list[dict]:
    alerts = []

    # High return-rate SKU alerts
    if sku_df is not None:
        overall_avg = float(sku_df["return_rate"].mean())
        for _, row in sku_df.iterrows():
            rr = float(row["return_rate"])
            if rr > overall_avg * 1.5 and rr > 0.2:
                alerts.append({
                    "severity": "HIGH",
                    "sku_id": row["sku_id"],
                    "name": row.get("name", row["sku_id"]),
                    "issue": "High Return Rate",
                    "detail": f"Return rate {rr*100:.1f}% is {rr/overall_avg:.1f}x the average",
                    "suggestion": "Review product listing, photos, and description accuracy",
                })

        # Colour-mismatch hotspot
        if "is_color_issue" in sku_df.columns:
            color_bad = sku_df[sku_df["is_color_issue"] > 0.5]
            for _, row in color_bad.iterrows():
                alerts.append({
                    "severity": "MEDIUM",
                    "sku_id": row["sku_id"],
                    "name": row.get("name", row["sku_id"]),
                    "issue": "Colour Mismatch Signals",
                    "detail": f"{row['is_color_issue']*100:.0f}% of returns mention colour discrepancy",
                    "suggestion": "Update photography with accurate colour reference, add colour disclaimer",
                })

        # Size confusion hotspot
        if "is_size_issue" in sku_df.columns:
            size_bad = sku_df[sku_df["is_size_issue"] > 0.4]
            for _, row in size_bad.iterrows():
                alerts.append({
                    "severity": "MEDIUM",
                    "sku_id": row["sku_id"],
                    "name": row.get("name", row["sku_id"]),
                    "issue": "Size Confusion",
                    "detail": f"{row['is_size_issue']*100:.0f}% of returns mention size/scale issues",
                    "suggestion": "Add scale reference photos, room-in-use images, and AR visualisation",
                })

        # High loss alerts
        if "total_cost" in sku_df.columns:
            loss_threshold = float(sku_df["total_cost"].quantile(0.75))
            high_loss = sku_df[sku_df["total_cost"] >= loss_threshold]
            for _, row in high_loss.iterrows():
                alerts.append({
                    "severity": "HIGH",
                    "sku_id": row["sku_id"],
                    "name": row.get("name", row["sku_id"]),
                    "issue": "High Return Loss",
                    "detail": f"Total return cost: ${row['total_cost']:,.0f}",
                    "suggestion": "Prioritise this SKU for listing improvement and pre-purchase visualisation",
                })

    # Cluster-based alerts from return-level data
    if "root_cause" in df.columns:
        for sku, group in df.groupby("sku_id"):
            top_causes = group["root_cause"].value_counts(normalize=True)
            for cause, ratio in top_causes.head(1).items():
                if ratio > 0.5:
                    alerts.append({
                        "severity": "LOW",
                        "sku_id": sku,
                        "name": group.get("name", pd.Series([sku])).iloc[0] if "name" in group.columns else sku,
                        "issue": f"Dominant Cluster Signal: {cause}",
                        "detail": f"{ratio*100:.0f}% of returns cluster around: {cause}",
                        "suggestion": f"Investigate root cause: {cause}",
                    })

    # Deduplicate by sku_id + issue
    seen = set()
    deduped = []
    for a in alerts:
        key = (a["sku_id"], a["issue"])
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    return sorted(deduped, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["severity"], 3))
