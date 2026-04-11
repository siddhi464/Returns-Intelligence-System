from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split


def train_loss_model(sku_df: pd.DataFrame) -> tuple[HistGradientBoostingRegressor, float]:
    feature_cols = ["avg_sentiment", "dominant_cluster", "interaction_count", "avg_rating",
                    "is_color_issue", "is_size_issue", "is_quality_issue", "is_personal_reason"]
    available = [c for c in feature_cols if c in sku_df.columns]
    X = sku_df[available].copy().fillna(0)
    y = sku_df["return_rate"].astype(float)

    if len(X) < 4:
        model = HistGradientBoostingRegressor(random_state=42)
        model.fit(X, y)
        return model, 0.0

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)
    r2 = float(model.score(X_test, y_test)) if len(y_test) else 0.0
    return model, r2


def predict_loss(
    model: HistGradientBoostingRegressor,
    sku_df: pd.DataFrame,
    *,
    cost_per_return: float = 77.0,
    order_volume_multiplier: float = 2.0,
    scenario_rate_delta: float = 9.0,
) -> list[dict]:
    feature_cols = ["avg_sentiment", "dominant_cluster", "interaction_count", "avg_rating",
                    "is_color_issue", "is_size_issue", "is_quality_issue", "is_personal_reason"]
    available = [c for c in feature_cols if c in sku_df.columns]
    X = sku_df[available].copy().fillna(0)

    pred_rate = np.clip(model.predict(X).astype(float), 0.0, 1.0)
    future_rate = np.clip(pred_rate + float(scenario_rate_delta), 0.0, 1.0)
    order_volume = (sku_df["interaction_count"].astype(float) * float(order_volume_multiplier)).clip(lower=1.0)

    # Actual loss from real return counts
    actual_loss = sku_df.get("total_cost", sku_df["return_rate"] * cost_per_return * order_volume)
    predicted_loss = future_rate * float(cost_per_return) * order_volume

    out = sku_df[["sku_id"]].copy()
    if "name" in sku_df.columns:
        out["name"] = sku_df["name"]
    if "category" in sku_df.columns:
        out["category"] = sku_df["category"]
    out["actual_loss"] = actual_loss.astype(float).round(2)
    out["predicted_loss"] = predicted_loss.astype(float).round(2)
    out["returns_count"] = sku_df["returns_count"].astype(int)
    out["return_rate_pct"] = (sku_df["return_rate"] * 100).round(1)
    out["loss_delta_pct"] = np.where(
        out["actual_loss"] > 0,
        ((out["predicted_loss"] - out["actual_loss"]) / out["actual_loss"] * 100.0).round(1),
        0.0,
    )
    return out.sort_values("predicted_loss", ascending=False).to_dict(orient="records")
