"""
WSI Sentinel — FastAPI backend (SCM intelligence).
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.cache import get_cache
from src.disposition_pipeline import build_disposition_insights
from src.pipeline import build_pipeline, compute_dashboard_outputs

app = FastAPI(title="WSI Sentinel SCM API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE = get_cache()
DATA_DIR = os.getenv("DATA_DIR", "data")
_PIPELINE_KEY = "pipeline:v2"
_DASHBOARD_KEY = "dashboard:v2"
_DISPOSITION_KEY = "disposition:v1"


def _get_pipeline():
    arts = CACHE.get(_PIPELINE_KEY)
    if arts is None:
        arts = build_pipeline(data_dir=DATA_DIR)
        CACHE.set(_PIPELINE_KEY, arts, ttl_seconds=3600)
    return arts


def _refresh_pipeline_loop(interval: int = 3600):
    interval = int(os.getenv("DATA_REFRESH_INTERVAL_S", interval))
    while True:
        time.sleep(interval)
        try:
            arts = build_pipeline(data_dir=DATA_DIR)
            CACHE.set(_PIPELINE_KEY, arts, ttl_seconds=interval + 120)
            CACHE.delete(_DASHBOARD_KEY)
            CACHE.delete(_DISPOSITION_KEY)
        except Exception as e:
            print(f"[refresh] Error: {e}")


threading.Thread(target=_refresh_pipeline_loop, daemon=True).start()


@app.get("/api/health")
def health():
    arts = _get_pipeline()
    return {
        "status": "ok",
        "total_returns": len(arts.merged_df),
        "model_metrics": {
            "risk_accuracy": round(float(arts.risk_accuracy), 4),
            "loss_r2": round(float(arts.loss_r2), 4),
        },
    }


@app.get("/api/dashboard")
def dashboard(
    cost_per_return: float = Query(77),
    order_volume_multiplier: float = Query(2),
    scenario_rate_delta: float = Query(9),
):
    cache_key = f"{_DASHBOARD_KEY}:{cost_per_return}:{order_volume_multiplier}:{scenario_rate_delta}"
    cached = CACHE.get(cache_key)
    if cached:
        return cached

    arts = _get_pipeline()
    out = compute_dashboard_outputs(
        arts,
        cost_per_return=cost_per_return,
        order_volume_multiplier=order_volume_multiplier,
        scenario_rate_delta=scenario_rate_delta,
    )
    CACHE.set(cache_key, out, ttl_seconds=60)
    return out


@app.get("/api/sku/{sku_id}")
def sku_detail(sku_id: str):
    import numpy as np

    def _safe(v):
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, float) and (v != v):
            return None
        return v

    arts = _get_pipeline()
    df = arts.clustered_df
    sku_rows = df[df["sku_id"] == sku_id].copy()
    if sku_rows.empty:
        return JSONResponse({"error": f"SKU {sku_id} not found"}, status_code=404)

    keep_cols = [
        c
        for c in [
            "return_id",
            "return_reason",
            "return_note",
            "return_date",
            "cost_of_return",
            "city",
            "state",
            "region",
            "zip_code",
            "root_cause",
            "sentiment_score",
        ]
        if c in sku_rows.columns
    ]
    returns_list = []
    for rec in sku_rows[keep_cols].to_dict(orient="records"):
        returns_list.append({k: _safe(v) for k, v in rec.items()})

    reason_counts = (
        {k: int(v) for k, v in sku_rows["return_reason"].value_counts().to_dict().items()}
        if "return_reason" in sku_rows.columns
        else {}
    )
    cluster_counts = (
        {k: int(v) for k, v in sku_rows["root_cause"].value_counts().to_dict().items()}
        if "root_cause" in sku_rows.columns
        else {}
    )

    product_info = {}
    for col in ["name", "category", "finish", "price"]:
        if col in sku_rows.columns:
            product_info[col] = _safe(sku_rows[col].iloc[0])

    return {
        "sku_id": sku_id,
        "product_info": product_info,
        "total_returns": int(len(sku_rows)),
        "total_cost": float(sku_rows["cost_of_return"].sum()) if "cost_of_return" in sku_rows.columns else 0,
        "avg_sentiment": float(sku_rows["sentiment_score"].mean()) if "sentiment_score" in sku_rows.columns else 0,
        "reason_breakdown": reason_counts,
        "cluster_breakdown": cluster_counts,
        "returns": returns_list[-50:],
    }


@app.get("/api/alerts")
def alerts():
    arts = _get_pipeline()
    out = compute_dashboard_outputs(arts)
    return {"alerts": out["alerts"]}


@app.get("/api/regions")
def regions():
    arts = _get_pipeline()
    out = compute_dashboard_outputs(arts)
    return out["region_insights"]


@app.get("/disposition_insights")
def disposition_insights(
    stress_wms: bool = Query(False, description="Simulate 99% hub capacity (stress test)"),
):
    cache_key = f"{_DISPOSITION_KEY}:{stress_wms}"
    cached = CACHE.get(cache_key)
    if cached:
        return cached
    data = build_disposition_insights(DATA_DIR, stress_wms=stress_wms, use_llm=True)
    CACHE.set(cache_key, data, ttl_seconds=120)
    return data


@app.post("/api/stress_test/toggle")
def stress_test_toggle(active: bool = Query(...)):
    """Invalidate disposition cache; clients should refetch with stress_wms query."""
    CACHE.delete(_DISPOSITION_KEY)
    return {"stress_mode": active, "hint": "GET /disposition_insights?stress_wms=true"}


@app.get("/api/network_map")
def network_map(stress_wms: bool = Query(False)):
    """Hubs and routed edges for map UI."""
    data = build_disposition_insights(DATA_DIR, stress_wms=stress_wms, use_llm=False)
    nodes = []
    path_wh = os.path.join(DATA_DIR, "warehouse_status.json")
    if not os.path.isfile(path_wh):
        path_wh = os.path.join(DATA_DIR, "wms_live.json")
    import json

    if os.path.isfile(path_wh):
        with open(path_wh, "r", encoding="utf-8") as f:
            wh = json.load(f)
        for w in wh:
            cap = 99 if stress_wms else int(w.get("current_capacity", 0))
            nodes.append(
                {
                    "id": w.get("hub_id"),
                    "label": w.get("name", w.get("hub_id")),
                    "lat": float(w.get("lat", 0)),
                    "lon": float(w.get("lon", 0)),
                    "capacity_pct": cap,
                }
            )
    edges = []

    for r in data["records"]:
        rt = r.get("routing", {})

        # ✅ If multi-leg exists → send ALL legs
        if "route_legs" in rt:
            for leg in rt["route_legs"]:
                edges.append(
                    {
                        "sku_id": r["sku_id"],
                        "hub": rt.get("target_hub"),
                        "hub_id": rt.get("hub_id"),
                        "from": leg.get("start"),
                        "to": leg.get("end"),
                        "action": r.get("recommended_action"),
                    }
                )
        else:
            # fallback (old logic)
            end = rt.get("route_end") or {}
            edges.append(
                {
                    "sku_id": r["sku_id"],
                    "hub": rt.get("target_hub"),
                    "hub_id": rt.get("hub_id"),
                    "from": rt.get("route_start"),
                    "to": end,
                    "action": r.get("recommended_action"),
                }
            )
    return {"nodes": nodes, "edges": edges, "stress_wms_active": stress_wms}


@app.post("/api/ingest_return")
async def ingest_return(body: dict[str, Any] = Body(default_factory=dict)):
    required = ["sku_id"]
    missing = [k for k in required if k not in body]
    if missing:
        return JSONResponse({"error": f"Missing fields: {missing}"}, status_code=400)

    csv_path = os.path.join(DATA_DIR, "returns.csv")
    existing = pd.read_csv(csv_path, on_bad_lines="skip") if os.path.exists(csv_path) else pd.DataFrame()

    import random
    import string
    from datetime import datetime

    new_id = "R" + "".join(random.choices(string.digits, k=6))

    new_row = {
        "return_id": new_id,
        "order_id": body.get("order_id", ""),
        "sku_id": body["sku_id"],
        "return_reason": body.get("return_reason", "no_longer_needed"),
        "return_note": body.get("return_note", ""),
        "return_date": datetime.now().strftime("%Y-%m-%d"),
        "cost_of_return": float(body.get("cost_of_return", 150.0)),
        "city": body.get("city", ""),
        "state": body.get("state", ""),
        "region": body.get("region", ""),
        "zip_code": int(body.get("zip_code", 10001)),
        "return_condition": body.get("return_condition", ""),
        "days_to_return": body.get("days_to_return", ""),
    }

    updated = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    updated.to_csv(csv_path, index=False)

    CACHE.delete(_PIPELINE_KEY)
    CACHE.delete(_DASHBOARD_KEY)
    CACHE.delete(_DISPOSITION_KEY)

    return {"status": "ingested", "return_id": new_id, "message": "Pipeline cache cleared."}


# SPA: serve built frontend from frontend/dist; else legacy static HTML
_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
_STATIC_LEGACY = os.path.join(os.path.dirname(__file__), "static", "index.html")


@app.get("/")
def root_index():
    index = os.path.join(_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    if os.path.isfile(_STATIC_LEGACY):
        return FileResponse(_STATIC_LEGACY)
    return JSONResponse({"detail": "No UI found. Build frontend or add static/index.html"}, status_code=404)


if os.path.isdir(_DIST) and os.path.isdir(os.path.join(_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
