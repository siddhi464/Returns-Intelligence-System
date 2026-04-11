"""
app.py — Returns Intelligence Dashboard Backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
Run: python app.py
"""
from __future__ import annotations

import json
import os
import threading
import time

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from src.cache import get_cache
from src.disposition_pipeline import build_disposition_insights
from src.pipeline import build_pipeline, compute_dashboard_outputs
from src.risk_model import prepare_sku_frame, predict_return_risk
from src.loss_model import predict_loss

app = Flask(__name__, static_folder="static")

CACHE = get_cache()
DATA_DIR = os.getenv("DATA_DIR", "data")
_PIPELINE_KEY = "pipeline:v2"
_DASHBOARD_KEY = "dashboard:v2"


def _get_pipeline():
    arts = CACHE.get(_PIPELINE_KEY)
    if arts is None:
        arts = build_pipeline(data_dir=DATA_DIR)
        CACHE.set(_PIPELINE_KEY, arts, ttl_seconds=3600)
    return arts


def _refresh_pipeline_loop(interval: int = 3600):
    """Background thread: rebuilds pipeline every hour (or DATA_REFRESH_INTERVAL_S env var)."""
    interval = int(os.getenv("DATA_REFRESH_INTERVAL_S", interval))
    while True:
        time.sleep(interval)
        try:
            arts = build_pipeline(data_dir=DATA_DIR)
            CACHE.set(_PIPELINE_KEY, arts, ttl_seconds=interval + 120)
            CACHE.delete(_DASHBOARD_KEY)
        except Exception as e:
            print(f"[refresh] Error: {e}")


threading.Thread(target=_refresh_pipeline_loop, daemon=True).start()


# ── Serve frontend ─────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return send_from_directory("static", "index.html")


# ── API endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    cost = float(request.args.get("cost_per_return", 150))
    multiplier = float(request.args.get("order_volume_multiplier", 10))
    delta = float(request.args.get("scenario_rate_delta", 0.0))

    cache_key = f"{_DASHBOARD_KEY}:{cost}:{multiplier}:{delta}"
    cached = CACHE.get(cache_key)
    if cached:
        return jsonify(cached)

    arts = _get_pipeline()
    out = compute_dashboard_outputs(arts, cost_per_return=cost,
                                    order_volume_multiplier=multiplier,
                                    scenario_rate_delta=delta)
    CACHE.set(cache_key, out, ttl_seconds=60)
    return jsonify(out)


@app.get("/api/sku/<sku_id>")
def sku_detail(sku_id: str):
    import numpy as np

    def _safe(v):
        if isinstance(v, (np.integer,)): return int(v)
        if isinstance(v, (np.floating,)): return float(v)
        if isinstance(v, float) and (v != v): return None
        return v

    arts = _get_pipeline()
    df = arts.clustered_df
    sku_rows = df[df["sku_id"] == sku_id].copy()
    if sku_rows.empty:
        return jsonify({"error": f"SKU {sku_id} not found"}), 404

    keep_cols = [c for c in ["return_id", "return_reason", "return_note",
                              "return_date", "cost_of_return", "city", "state",
                              "region", "root_cause", "sentiment_score"] if c in sku_rows.columns]
    returns_list = []
    for rec in sku_rows[keep_cols].to_dict(orient="records"):
        returns_list.append({k: _safe(v) for k, v in rec.items()})

    reason_counts = {k: int(v) for k, v in sku_rows["return_reason"].value_counts().to_dict().items()} if "return_reason" in sku_rows.columns else {}
    cluster_counts = {k: int(v) for k, v in sku_rows["root_cause"].value_counts().to_dict().items()} if "root_cause" in sku_rows.columns else {}

    product_info = {}
    for col in ["name", "category", "finish", "price"]:
        if col in sku_rows.columns:
            product_info[col] = _safe(sku_rows[col].iloc[0])

    return jsonify({
        "sku_id": sku_id,
        "product_info": product_info,
        "total_returns": int(len(sku_rows)),
        "total_cost": float(sku_rows["cost_of_return"].sum()) if "cost_of_return" in sku_rows.columns else 0,
        "avg_sentiment": float(sku_rows["sentiment_score"].mean()) if "sentiment_score" in sku_rows.columns else 0,
        "reason_breakdown": reason_counts,
        "cluster_breakdown": cluster_counts,
        "returns": returns_list[-50:],
    })


@app.get("/api/alerts")
def alerts():
    arts = _get_pipeline()
    out = compute_dashboard_outputs(arts)
    return jsonify({"alerts": out["alerts"]})


@app.get("/api/regions")
def regions():
    arts = _get_pipeline()
    out = compute_dashboard_outputs(arts)
    return jsonify(out["region_insights"])

@app.get("/api/disposition_insights")
def disposition_insights():
    """
    Golden Records per SKU for NRV + routing.
    Query params:
      - stress_wms=1|0: if 1, spikes all hubs to 99% capacity
      - use_llm=1|0: if 1, enables Gemini/Groq grading when keys are configured
    """
    stress = request.args.get("stress_wms", "0") in ("1", "true", "True")
    use_llm = request.args.get("use_llm", "0") in ("1", "true", "True")

    cache_key = f"disposition:v1:{int(stress)}:{int(use_llm)}"
    cached = CACHE.get(cache_key)
    if cached:
        return jsonify(cached)

    out = build_disposition_insights(DATA_DIR, stress_wms=stress, use_llm=use_llm)
    CACHE.set(cache_key, out, ttl_seconds=60)
    return jsonify(out)


@app.get("/api/network_map")
def network_map():
    """
    Hubs + routed edges (origin → hub) for map UI.
    Query params:
      - stress_wms=1|0
    """
    stress = request.args.get("stress_wms", "0") in ("1", "true", "True")
    cache_key = f"network_map:v1:{int(stress)}"
    cached = CACHE.get(cache_key)
    if cached:
        return jsonify(cached)

    data = build_disposition_insights(DATA_DIR, stress_wms=stress, use_llm=False)

    wh_path = os.path.join(DATA_DIR, "warehouse_status.json")
    if not os.path.isfile(wh_path):
        wh_path = os.path.join(DATA_DIR, "wms_live.json")

    nodes = []
    if os.path.isfile(wh_path):
        with open(wh_path, "r", encoding="utf-8") as f:
            wh = json.load(f)
        for w in wh:
            cap = 99 if stress else int(w.get("current_capacity", 0))
            nodes.append({
                "id": str(w.get("hub_id", "")),
                "label": str(w.get("name", w.get("hub_id", ""))),
                "lat": float(w.get("lat", 0) or 0),
                "lon": float(w.get("lon", 0) or 0),
                "capacity_pct": cap,
            })

    edges = []
    for r in data.get("records", []):
        rt = r.get("routing", {}) or {}
        edges.append({
            "sku_id": r.get("sku_id"),
            "hub": rt.get("target_hub"),
            "hub_id": rt.get("hub_id"),
            "from": rt.get("route_start"),
            "to": rt.get("route_end"),
            "action": r.get("recommended_action"),
        })

    out = {"nodes": nodes, "edges": edges, "stress_wms_active": stress}
    CACHE.set(cache_key, out, ttl_seconds=60)
    return jsonify(out)


@app.post("/api/ingest_return")
def ingest_return():
    """
    Real-time ingestion: POST a new return row.
    Body JSON: { sku_id, return_reason, return_note, cost_of_return, city, state, region }
    Appends to returns.csv and busts pipeline cache so next /api/dashboard call rebuilds.
    """
    data = request.get_json(force=True)
    required = ["sku_id"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    # Read existing, append, write back
    csv_path = os.path.join(DATA_DIR, "returns.csv")
    existing = pd.read_csv(csv_path, on_bad_lines="skip") if os.path.exists(csv_path) else pd.DataFrame()

    import random, string
    from datetime import datetime
    new_id = "R" + "".join(random.choices(string.digits, k=6))

    new_row = {
        "return_id": new_id,
        "order_id": data.get("order_id", ""),
        "sku_id": data["sku_id"],
        "return_reason": data.get("return_reason", "no_longer_needed"),
        "return_note": data.get("return_note", ""),
        "return_date": datetime.now().strftime("%Y-%m-%d"),
        "cost_of_return": float(data.get("cost_of_return", 150.0)),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "region": data.get("region", ""),
    }

    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(csv_path, index=False)

    # Bust cache so next dashboard call re-trains
    CACHE.delete(_PIPELINE_KEY)
    CACHE.delete(_DASHBOARD_KEY)

    return jsonify({"status": "ingested", "return_id": new_id, "message": "Pipeline cache cleared. Next dashboard call will rebuild."})


@app.get("/api/health")
def health():
    arts = _get_pipeline()
    return jsonify({
        "status": "ok",
        "total_returns": len(arts.merged_df),
        "model_metrics": {
            "risk_accuracy": round(float(arts.risk_accuracy), 4),
            "loss_r2": round(float(arts.loss_r2), 4),
        }
    })


if __name__ == "__main__":
    print("Returns Intelligence Dashboard starting on http://localhost:5000")
    app.run(debug=True, port=5000)
