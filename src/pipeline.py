from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

from src.data_processing import merge_data
from src.nlp_engine import ClusterArtifacts, add_sentiment, cluster_issues, combine_text, tag_issue_type
from src.risk_model import prepare_sku_frame, train_ensemble_model, predict_return_risk
from src.loss_model import train_loss_model, predict_loss
from sklearn.ensemble import HistGradientBoostingRegressor
from src.alert_engine import generate_smart_alerts
from src.region_analysis import region_return_analysis, region_root_cause_mapping, hotspot_detection


@dataclass
class PipelineArtifacts:
    merged_df: pd.DataFrame
    clustered_df: pd.DataFrame
    sku_df: pd.DataFrame
    clusters: ClusterArtifacts
    risk_model: object
    risk_accuracy: float
    loss_model: HistGradientBoostingRegressor
    loss_r2: float


def build_pipeline(data_dir: str = "data") -> PipelineArtifacts:
    df = merge_data(data_dir=data_dir)
    df = combine_text(df)
    df = add_sentiment(df)
    df = tag_issue_type(df)
    df, clusters = cluster_issues(df)

    sku_df = prepare_sku_frame(df)
    risk_model, acc, _ = train_ensemble_model(df)
    loss_model, r2 = train_loss_model(sku_df)

    return PipelineArtifacts(
        merged_df=df,
        clustered_df=df,
        sku_df=sku_df,
        clusters=clusters,
        risk_model=risk_model,
        risk_accuracy=acc,
        loss_model=loss_model,
        loss_r2=r2,
    )


def compute_dashboard_outputs(
    artifacts: PipelineArtifacts,
    *,
    cost_per_return: float = 77.0,
    order_volume_multiplier: float = 2.0,
    scenario_rate_delta: float = 9.0,
) -> dict:
    df = artifacts.clustered_df
    sku_df = artifacts.sku_df

    alerts = generate_smart_alerts(df, sku_df)
    risk = predict_return_risk(artifacts.risk_model, sku_df)
    loss_preds = predict_loss(
        artifacts.loss_model, sku_df,
        cost_per_return=cost_per_return,
        order_volume_multiplier=order_volume_multiplier,
        scenario_rate_delta=scenario_rate_delta,
    )

    regions = region_return_analysis(df)
    region_issues = region_root_cause_mapping(df)
    hotspots = hotspot_detection(regions["by_region"])

    # Summary KPIs
    total_returns = int(len(df))
    total_loss = float(df["cost_of_return"].sum()) if "cost_of_return" in df.columns else 0.0
    avg_return_rate = float(sku_df["return_rate"].mean())
    top_sku_by_loss = loss_preds[0]["sku_id"] if loss_preds else "N/A"

    # SKU-level breakdown for charts
    sku_breakdown = []
    for row in risk:
        sku_id = row["sku_id"]
        loss_row = next((l for l in loss_preds if l["sku_id"] == sku_id), {})
        sku_breakdown.append({
            **row,
            "actual_loss": loss_row.get("actual_loss", 0),
            "predicted_loss": loss_row.get("predicted_loss", 0),
            "return_rate_pct": loss_row.get("return_rate_pct", 0),
        })

    # Category breakdown
    if "category" in df.columns:
        cat_data = (
            df.groupby("category")
            .agg(
                returns=("return_id", "count") if "return_id" in df.columns else ("sku_id", "count"),
                total_cost=("cost_of_return", "sum") if "cost_of_return" in df.columns else ("sku_id", "count"),
            )
            .reset_index()
            .sort_values("returns", ascending=False)
            .to_dict(orient="records")
        )
    else:
        cat_data = []

    # Issue type breakdown across all returns
    issue_totals = {
        "color_mismatch": int(df.get("is_color_issue", pd.Series([0] * len(df))).sum()),
        "size_confusion": int(df.get("is_size_issue", pd.Series([0] * len(df))).sum()),
        "quality_issue": int(df.get("is_quality_issue", pd.Series([0] * len(df))).sum()),
        "personal_reason": int(df.get("is_personal_reason", pd.Series([0] * len(df))).sum()),
    }

    return {
        "kpis": {
            "total_returns": total_returns,
            "total_loss": round(total_loss, 2),
            "avg_return_rate_pct": round(avg_return_rate * 100, 1),
            "top_sku_by_loss": top_sku_by_loss,
            "active_alerts": len([a for a in alerts if a["severity"] == "HIGH"]),
        },
        "alerts": alerts,
        "sku_breakdown": sku_breakdown,
        "loss_predictions": loss_preds,
        "issue_totals": issue_totals,
        "category_breakdown": cat_data,
        "clusters": {
            "keywords": {str(k): v for k, v in artifacts.clusters.cluster_keywords.items()},
            "labels": {str(k): v for k, v in artifacts.clusters.cluster_labels.items()},
        },
        "region_insights": {
            "by_city": regions["by_city"],
            "by_state": regions["by_state"],
            "by_region": regions["by_region"],
            "root_causes": region_issues,
            "hotspots": hotspots,
        },
        "model_metrics": {
            "risk_model_accuracy": round(float(artifacts.risk_accuracy), 4),
            "loss_model_r2": round(float(artifacts.loss_r2), 4),
        },
    }
