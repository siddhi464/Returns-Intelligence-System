from __future__ import annotations
import numpy as np
import pandas as pd


def region_return_analysis(df: pd.DataFrame) -> dict:
    data = df.copy()
    for col in ["city", "state", "region"]:
        if col not in data.columns:
            data[col] = "Unknown"
        data[col] = data[col].fillna("Unknown").astype(str)

    total = float(len(data))

    def _agg(level: str, key: str) -> list[dict]:
        grp = (
            data.groupby(level, dropna=False)
            .agg(total_returns=(level, "count"),
                 total_loss=("cost_of_return", "sum") if "cost_of_return" in data.columns else (level, "count"))
            .reset_index()
        )
        grp["return_share_pct"] = (grp["total_returns"] / total * 100).round(2) if total else 0
        return grp.rename(columns={level: key}).sort_values("total_returns", ascending=False).to_dict(orient="records")

    return {
        "by_city":   _agg("city",   "city"),
        "by_state":  _agg("state",  "state"),
        "by_region": _agg("region", "region"),
    }


def region_root_cause_mapping(df: pd.DataFrame) -> list[dict]:
    tmp = df.copy()
    for col in ["region", "root_cause", "sentiment_score"]:
        if col not in tmp.columns:
            tmp[col] = "Unknown" if col != "sentiment_score" else 0.0
    tmp["region"] = tmp["region"].fillna("Unknown").astype(str)
    tmp["root_cause"] = tmp["root_cause"].fillna("misc").astype(str)
    tmp["sentiment_score"] = tmp["sentiment_score"].fillna(0.0).astype(float)

    out = []
    for region, g in tmp.groupby("region"):
        total = float(len(g))
        top_issue = g["root_cause"].value_counts().idxmax() if total else "misc"
        top_count = float((g["root_cause"] == top_issue).sum())
        out.append({
            "region": region,
            "top_issue": str(top_issue),
            "percentage": round((top_count / total * 100.0) if total else 0.0, 2),
            "sentiment_score": round(float(g["sentiment_score"].mean()), 3),
            "total_returns": int(total),
        })
    return sorted(out, key=lambda x: x["total_returns"], reverse=True)


def hotspot_detection(region_rows: list[dict]) -> list[dict]:
    if not region_rows:
        return []
    shares = np.array([float(r.get("return_share_pct", 0.0)) for r in region_rows], dtype=float)
    mu, sigma = float(np.mean(shares)), float(np.std(shares))
    threshold = mu + 1.0 * sigma
    out = []
    for r in region_rows:
        share = float(r.get("return_share_pct", 0.0))
        if share >= threshold and share > 0:
            out.append({
                "region": r.get("region", r.get("city", r.get("state", "?"))),
                "return_share_pct": share,
                "total_returns": r.get("total_returns", 0),
                "status": "HIGH_RETURN_HOTSPOT",
            })
    return sorted(out, key=lambda x: x["return_share_pct"], reverse=True)
