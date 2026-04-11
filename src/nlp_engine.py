from __future__ import annotations
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_sia = SentimentIntensityAnalyzer()

# Keyword patterns for explicit issue tagging (complementing ML clusters)
COLOR_KEYWORDS = r"colour|color|tone|dark|light|grey|gray|warm|cool|brown|gold|brass|finish|photo|picture|different|mismatch"
SIZE_KEYWORDS  = r"size|large|small|big|huge|tiny|dimension|scale|fit|space|room|ceiling|floor"
QUALITY_KEYWORDS = r"scratch|damage|defect|broken|crack|chip|dent|wobbly|loose|rough|grain|edge|surface|quality"
PERSONAL_KEYWORDS = r"cancel|changed mind|no longer|moved|event|renovation|mistake|duplicate|gift|bought wrong"


def _clean_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(product|item|received|order|delivery|purchased|bought)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def combine_text(df: pd.DataFrame) -> pd.DataFrame:
    df["combined_text"] = (
        df.get("return_note", pd.Series([""])).fillna("").astype(str)
        + " "
        + df.get("review_text_agg", pd.Series([""])).fillna("").astype(str)
        + " "
        + df.get("transcript_agg", pd.Series([""])).fillna("").astype(str)
    ).apply(_clean_text)
    return df


def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    df["sentiment_score"] = df["combined_text"].apply(
        lambda x: float(_sia.polarity_scores(x)["compound"])
    )
    return df


def tag_issue_type(df: pd.DataFrame) -> pd.DataFrame:
    """Rule-based issue type tagging from combined text."""
    text = df["combined_text"].fillna("")
    df["is_color_issue"]    = text.str.contains(COLOR_KEYWORDS, case=False, regex=True).astype(int)
    df["is_size_issue"]     = text.str.contains(SIZE_KEYWORDS,  case=False, regex=True).astype(int)
    df["is_quality_issue"]  = text.str.contains(QUALITY_KEYWORDS, case=False, regex=True).astype(int)
    df["is_personal_reason"] = text.str.contains(PERSONAL_KEYWORDS, case=False, regex=True).astype(int)
    return df


@dataclass(frozen=True)
class ClusterArtifacts:
    kmeans: KMeans
    vectorizer: TfidfVectorizer
    cluster_keywords: dict[int, list[str]]
    cluster_labels: dict[int, str]


def _infer_k(X, k_min: int, k_max: int, random_state: int) -> int:
    n = X.shape[0]
    upper = min(k_max, max(k_min, n - 1))
    if n < (k_min + 1) or upper <= k_min:
        return max(2, min(4, n)) if n >= 2 else 1
    best_k, best_score = k_min, -1.0
    for k in range(k_min, upper + 1):
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k


def cluster_issues(
    df: pd.DataFrame,
    *,
    prefer_k: int | None = None,
    k_range: tuple[int, int] = (3, 8),
    max_features: int = 1500,
    random_state: int = 42,
) -> tuple[pd.DataFrame, ClusterArtifacts]:
    texts = df["combined_text"].fillna("").astype(str).tolist()
    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=max_features,
        ngram_range=(1, 2), min_df=1,
    )
    X = vectorizer.fit_transform(texts)

    if X.shape[0] < 2:
        df["cluster_id"] = 0
        artifacts = ClusterArtifacts(
            kmeans=KMeans(n_clusters=1, random_state=random_state, n_init=1),
            vectorizer=vectorizer,
            cluster_keywords={0: []},
            cluster_labels={0: "misc"},
        )
        df["root_cause"] = "misc"
        return df, artifacts

    k_min, k_max = k_range
    k = prefer_k if prefer_k is not None else _infer_k(X, k_min=k_min, k_max=k_max, random_state=random_state)
    k = int(max(2, min(k, X.shape[0] - 1)))

    kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    df["cluster_id"] = kmeans.fit_predict(X).astype(int)

    cluster_keywords = _get_keywords(kmeans, vectorizer, top_n=8)
    cluster_labels = _label_clusters(cluster_keywords)
    df["root_cause"] = df["cluster_id"].map(cluster_labels).fillna("misc")

    return df, ClusterArtifacts(
        kmeans=kmeans, vectorizer=vectorizer,
        cluster_keywords=cluster_keywords, cluster_labels=cluster_labels,
    )


def _get_keywords(kmeans: KMeans, vectorizer: TfidfVectorizer, top_n: int = 8) -> dict[int, list[str]]:
    terms = np.array(vectorizer.get_feature_names_out())
    out: dict[int, list[str]] = {}
    for cid, center in enumerate(kmeans.cluster_centers_):
        top_idx = np.argsort(center)[-top_n:][::-1]
        out[int(cid)] = [t for t in terms[top_idx].tolist() if t.strip()]
    return out


def _label_clusters(cluster_keywords: dict[int, list[str]], max_len: int = 40) -> dict[int, str]:
    labels: dict[int, str] = {}
    for cid, words in cluster_keywords.items():
        label = " / ".join(words[:3]) if words else "misc"
        labels[int(cid)] = label[:max_len].rstrip(" /")
    return labels
