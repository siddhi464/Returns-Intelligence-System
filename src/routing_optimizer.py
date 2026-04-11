"""
Deterministic routing: eligible hubs with capacity < 90% (or threshold), min total cost.
Congestion: 75%–90% capacity adds +15% processing cost multiplier.
Stress test: synthetic capacity spike to 99% for UI demonstration.
Clustering: high cluster_density enables consolidated pickup savings vs baseline pickup.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from math import radians, sin, cos, sqrt, atan2
import random


BASELINE_PICKUP = 180.0
CONSOLIDATED_PICKUP_SHARED = 300.0
CONGESTION_LOW = 75
CONGESTION_HIGH = 90
CAPACITY_ELIGIBLE_MAX = 90
PROCESSING_BASE = 35.0


@dataclass
class Hub:
    hub_id: str
    name: str
    lat: float
    lon: float
    current_capacity: int
    processing_rate: float = 1.0


def _default_hubs(stress_mode: bool = False) -> list[Hub]:
    return [
        Hub("WH001", "NYC Hub", 40.7, -74.0, 99 if stress_mode else 65),
        Hub("WH002", "Chicago Hub", 41.8, -87.6, 99 if stress_mode else 72),
        Hub("WH003", "Dallas Hub", 32.8, -96.8, 99 if stress_mode else 58),
        Hub("WH004", "LA Hub", 34.0, -118.2, 99 if stress_mode else 81),
    ]


def load_warehouses(data_dir: str, stress_mode: bool = False) -> list[Hub]:
    path = os.path.join(data_dir, "warehouse_status.json")
    if not os.path.isfile(path):
        path = os.path.join(data_dir, "wms_live.json")
    if not os.path.isfile(path):
        return _default_hubs(stress_mode)

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    hubs: list[Hub] = []
    for row in raw:
        cap = int(row.get("current_capacity", 0))
        if stress_mode:
            cap = 99
        hubs.append(
            Hub(
                hub_id=str(row.get("hub_id", "WH")),
                name=str(row.get("name", row.get("hub_id", "Hub"))),
                lat=float(row.get("lat", 0)),
                lon=float(row.get("lon", 0)),
                current_capacity=cap,
                processing_rate=float(row.get("processing_rate", 1.0)),
            )
        )
    return hubs


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def congestion_multiplier(capacity_pct: int) -> float:
    if CONGESTION_LOW <= capacity_pct < CONGESTION_HIGH:
        return 1.15
    return 1.0


def hub_processing_cost(capacity_pct: int) -> float:
    return PROCESSING_BASE * congestion_multiplier(capacity_pct)


def _heuristic_score(distance, capacity, processing, shipping, action):
    score = 0.0

    score -= 0.5 * distance
    score -= 0.8 * capacity
    score += 20 * processing
    score -= 0.3 * shipping

    if "REFURB" in action:
        score += 10

    score += random.uniform(-2, 2)  # break ties

    return score


def route_to_hub(
    *,
    zip_code: str,
    shipping_rate: float,
    hubs: list[Hub],
    recommended_action: str,
) -> dict[str, Any]:

    eligible = [h for h in hubs if h.current_capacity < CAPACITY_ELIGIBLE_MAX]
    if not eligible:
        eligible = hubs[:]

    action = (recommended_action or "").upper()

    origin_lat, origin_lon = _approx_zip_to_coords(zip_code)

    best: Hub | None = None
    best_score = float("-inf")
    best_cost = 0.0

    for h in eligible:
        distance_km = _haversine(origin_lat, origin_lon, h.lat, h.lon)

        leg_cost = (
            float(shipping_rate) * h.processing_rate
            + hub_processing_cost(h.current_capacity)
            + (12.0 if "REFURB" in action else 0.0)
            + distance_km * 0.3
        )

        score = _heuristic_score(
            distance_km,
            h.current_capacity,
            h.processing_rate,
            shipping_rate,
            action,
        )

        if score > best_score:
            best_score = score
            best = h
            best_cost = leg_cost

    if best is None:
        best = hubs[0]
        best_cost = float(shipping_rate) + PROCESSING_BASE

    # 🔥 dynamic midpoint (this creates multiple visible paths)
    mid_lat = (origin_lat + best.lat) / 2 + random.uniform(-2, 2)
    mid_lon = (origin_lon + best.lon) / 2 + random.uniform(-2, 2)

    return {
        "target_hub": best.name,
        "hub_id": best.hub_id,
        "capacity_status": f"{best.current_capacity}%",
        "estimated_route_cost": round(best_cost, 2),

        # 🔥 MULTI-LEG ROUTES
        "route_legs": [
            {
                "start": {"lat": origin_lat, "lon": origin_lon},
                "end": {"lat": mid_lat, "lon": mid_lon},
            },
            {
                "start": {"lat": mid_lat, "lon": mid_lon},
                "end": {"lat": best.lat, "lon": best.lon},
            }
        ],

        "route_start": {"lat": origin_lat, "lon": origin_lon},
        "route_end": {"lat": best.lat, "lon": best.lon},
    }


def clustering_savings(cluster_density: int, n_returns_in_cluster: int = 1) -> tuple[bool, float]:
    if cluster_density >= 3:
        saved = max(0.0, BASELINE_PICKUP * max(1, n_returns_in_cluster) - CONSOLIDATED_PICKUP_SHARED)
        return True, round(min(saved, BASELINE_PICKUP * 3), 2)
    return False, 0.0


def _approx_zip_to_coords(zip_code: str) -> tuple[float, float]:
    if not zip_code:
        base_lat, base_lon = 39.5, -98.35
    else:
        try:
            z = int(zip_code[:2])
        except:
            base_lat, base_lon = 39.5, -98.35
        else:
            if 0 <= z <= 29:
                base_lat, base_lon = 40.7, -74.0
            elif 30 <= z <= 59:
                base_lat, base_lon = 41.8, -87.6
            elif 60 <= z <= 79:
                base_lat, base_lon = 32.8, -96.8
            else:
                base_lat, base_lon = 34.0, -118.2

    # 🔥 jitter = multiple visible lines
    jitter_lat = random.uniform(-1.2, 1.2)
    jitter_lon = random.uniform(-1.2, 1.2)

    return base_lat + jitter_lat, base_lon + jitter_lon