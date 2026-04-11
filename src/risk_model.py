from __future__ import annotations
from typing import Union, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def prepare_sku_frame(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    if "sentiment_score" not in tmp.columns:
        tmp["sentiment_score"] = 0.0
    if "cluster_id" not in tmp.columns:
        tmp["cluster_id"] = 0

    agg_dict: dict = {
        "avg_sentiment": ("sentiment_score", "mean"),
        "dominant_cluster": ("cluster_id", lambda s: int(s.value_counts().index[0]) if len(s) else 0),
        "avg_rating": ("avg_rating", "mean") if "avg_rating" in tmp.columns else ("cluster_id", "count"),
        "is_color_issue": ("is_color_issue", "mean") if "is_color_issue" in tmp.columns else ("cluster_id", lambda s: 0),
        "is_size_issue": ("is_size_issue", "mean") if "is_size_issue" in tmp.columns else ("cluster_id", lambda s: 0),
        "is_quality_issue": ("is_quality_issue", "mean") if "is_quality_issue" in tmp.columns else ("cluster_id", lambda s: 0),
        "is_personal_reason": ("is_personal_reason", "mean") if "is_personal_reason" in tmp.columns else ("cluster_id", lambda s: 0),
        "total_cost": ("cost_of_return", "sum") if "cost_of_return" in tmp.columns else ("cluster_id", lambda s: 0),
    }

    if "return_id" in tmp.columns:
        agg_dict["returns_count"] = ("return_id", "count")
    else:
        agg_dict["returns_count"] = ("sku_id", "count")

    if "review_count" in tmp.columns:
        agg_dict["review_count"] = ("review_count", "max")
    else:
        agg_dict["review_count"] = ("sku_id", "size")

    if "contact_count" in tmp.columns:
        agg_dict["contact_count"] = ("contact_count", "max")
    else:
        agg_dict["contact_count"] = ("sku_id", "size")

    # Include product metadata if available
    for col in ["name", "category", "finish", "price"]:
        if col in tmp.columns:
            agg_dict[col] = (col, "first")

    sku_df = tmp.groupby("sku_id", dropna=False).agg(**agg_dict).reset_index()

    sku_df["interaction_count"] = (
        sku_df["returns_count"] + sku_df["review_count"] + sku_df["contact_count"]
    ).clip(lower=1)
    sku_df["return_rate"] = (sku_df["returns_count"] / sku_df["interaction_count"]).clip(0, 1)
    sku_df["avg_rating"] = sku_df["avg_rating"].fillna(3.0)

    return sku_df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    sku_df = prepare_sku_frame(df)
    threshold = float(sku_df["return_rate"].median())
    sku_df["return_flag"] = (sku_df["return_rate"] >= threshold).astype(int)
    feature_cols = ["avg_sentiment", "dominant_cluster", "interaction_count", "avg_rating",
                    "is_color_issue", "is_size_issue", "is_quality_issue", "is_personal_reason"]
    available = [c for c in feature_cols if c in sku_df.columns]
    X = sku_df[available].copy().fillna(0)
    y = sku_df["return_flag"].copy()
    return X, y, sku_df


def train_ensemble_model(df: pd.DataFrame) -> tuple[Union[VotingClassifier, Any], float, pd.DataFrame]:
    X, y, sku_df = prepare_features(df)
    if len(X) < 4:
        # Not enough data — return a dummy
        from sklearn.dummy import DummyClassifier
        dummy = DummyClassifier(strategy="most_frequent")
        dummy.fit(X, y)
        return dummy, 0.0, sku_df

    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )
    ensemble = VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=2000)),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=42)),
            ("gb", GradientBoostingClassifier(random_state=42)),
        ],
        voting="soft",
    )
    ensemble.fit(X_train, y_train)
    preds = ensemble.predict(X_test)
    acc = float(accuracy_score(y_test, preds)) if len(y_test) else 0.0
    return ensemble, acc, sku_df


def predict_return_risk(model, sku_df: pd.DataFrame) -> list[dict]:
    feature_cols = ["avg_sentiment", "dominant_cluster", "interaction_count", "avg_rating",
                    "is_color_issue", "is_size_issue", "is_quality_issue", "is_personal_reason"]
    available = [c for c in feature_cols if c in sku_df.columns]
    X = sku_df[available].copy().fillna(0)
    probs = model.predict_proba(X)[:, 1]
    out = sku_df.copy()
    out["return_risk_score"] = (probs * 100).round(1)

    keep = ["sku_id", "return_risk_score", "return_rate", "returns_count",
            "total_cost", "avg_rating", "avg_sentiment"]
    for col in ["name", "category", "finish", "price"]:
        if col in out.columns:
            keep.append(col)
    keep = [c for c in keep if c in out.columns]
    return out[keep].sort_values("return_risk_score", ascending=False).to_dict(orient="records")
