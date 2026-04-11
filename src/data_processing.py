from __future__ import annotations

import os

import pandas as pd


def load_product_frame(data_dir: str = "data") -> pd.DataFrame:
    """Load product_master.csv if present, else products.csv; normalize columns."""
    pm = os.path.join(data_dir, "product_master.csv")
    legacy = os.path.join(data_dir, "products.csv")
    path = pm if os.path.isfile(pm) else legacy
    df = pd.read_csv(path, on_bad_lines="skip")
    if "product_name" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"product_name": "name"})
    if "name" not in df.columns:
        df["name"] = df.get("sku_id", "").astype(str)
    if "price" not in df.columns:
        df["price"] = 0.0
    return df


def load_data(data_dir: str = "data") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    returns = pd.read_csv(f"{data_dir}/returns.csv", on_bad_lines="skip")
    reviews = pd.read_csv(f"{data_dir}/reviews.csv", on_bad_lines="skip")
    contacts = pd.read_csv(f"{data_dir}/cs_contacts.csv", on_bad_lines="skip")
    products = load_product_frame(data_dir)
    return returns, reviews, contacts, products


def merge_data(data_dir: str = "data") -> pd.DataFrame:
    returns, reviews, contacts, products = load_data(data_dir=data_dir)

    for col in [
        "return_note",
        "return_reason",
        "city",
        "state",
        "region",
        "return_date",
        "cost_of_return",
        "zip_code",
        "return_condition",
        "days_to_return",
    ]:
        if col not in returns.columns:
            returns[col] = pd.NA

    returns["cost_of_return"] = pd.to_numeric(returns["cost_of_return"], errors="coerce").fillna(150.0)
    if returns["zip_code"].isna().all():
        returns["zip_code"] = 10001

    returns["zip_code"] = pd.to_numeric(returns["zip_code"], errors="coerce").fillna(10001).astype(int)

    if "review_text" not in reviews.columns:
        reviews["review_text"] = pd.NA
    if "rating" not in reviews.columns:
        reviews["rating"] = pd.NA

    if "transcript" not in contacts.columns:
        contacts["transcript"] = pd.NA

    prod_cols = ["sku_id", "name", "category", "finish", "price"]
    for c in prod_cols:
        if c not in products.columns:
            if c == "category":
                products[c] = "General"
            elif c == "finish":
                products[c] = "Standard"
            elif c == "name":
                products[c] = products.get("sku_id", "").astype(str)
            else:
                products[c] = pd.NA

    reviews_sku = (
        reviews.groupby("sku_id", dropna=False)
        .agg(
            review_text_agg=("review_text", lambda s: " ".join(s.dropna().astype(str).tolist())),
            avg_rating=("rating", "mean"),
            review_count=("review_id", "count") if "review_id" in reviews.columns else ("review_text", "count"),
        )
        .reset_index()
    )

    contacts_sku = (
        contacts.groupby("sku_id", dropna=False)
        .agg(
            transcript_agg=("transcript", lambda s: " ".join(s.dropna().astype(str).tolist())),
            contact_count=("contact_id", "count") if "contact_id" in contacts.columns else ("transcript", "count"),
        )
        .reset_index()
    )

    merged = (
        returns.merge(reviews_sku, on="sku_id", how="left")
        .merge(contacts_sku, on="sku_id", how="left")
        .merge(products[prod_cols], on="sku_id", how="left")
    )

    merged["review_text_agg"] = merged["review_text_agg"].fillna("")
    merged["transcript_agg"] = merged["transcript_agg"].fillna("")
    merged["avg_rating"] = merged["avg_rating"].fillna(3.0)
    merged["review_count"] = merged["review_count"].fillna(0).astype(int)
    merged["contact_count"] = merged["contact_count"].fillna(0).astype(int)
    merged["name"] = merged["name"].fillna("Unknown Product")
    merged["category"] = merged["category"].fillna("Uncategorized")
    merged["finish"] = merged["finish"].fillna("Unknown")
    merged["price"] = pd.to_numeric(merged.get("price", pd.Series([0] * len(merged))), errors="coerce").fillna(0.0)

    return merged
