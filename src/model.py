"""Rolling Isolation Forest scoring with plain-language reasons."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


MODEL_FEATURES = [
    "prior_30day_units",
    "threshold_utilization",
    "purchase_count_30d",
    "locations_30d",
    "days_since_previous_purchase",
    "early_purchase",
    "purchase_after_rejection",
    "personal_baseline_deviation",
    "customers_collected_for_90d",
    "authorization_customer_count",
    "previous_alerts_90d",
    "near_threshold",
    "unauthorized_product_switch",
]


def _reason_codes(row) -> list[str]:
    reasons = []
    if row.locations_30d > 2:
        reasons.append("More than two locations")
    if row.purchase_after_rejection:
        reasons.append("Attempt after rejection")
    if row.customers_collected_for_90d >= 3:
        reasons.append("Shared collector")
    if row.authorization_customer_count >= 2:
        reasons.append("Reused authorization")
    if row.unauthorized_product_switch:
        reasons.append("Unauthorized product change")
    if row.near_threshold:
        reasons.append("Near-threshold activity")
    if row.early_purchase:
        reasons.append("Earlier than expected supply")
    if row.personal_baseline_deviation >= 2:
        reasons.append("Increase from personal baseline")
    if not reasons:
        reasons.append("Unusual combined behaviour")
    return reasons[:2]


def score_monthly(features: pd.DataFrame, seed: int = 20250929) -> pd.DataFrame:
    scored = features.copy()
    scored["attempt_datetime"] = pd.to_datetime(scored["attempt_datetime"])
    scored["anomaly_score"] = np.nan
    scored["model_version"] = ""
    first_score_month = (scored["attempt_datetime"].min() + pd.DateOffset(months=3)).to_period("M")
    last_month = scored["attempt_datetime"].max().to_period("M")

    for period in pd.period_range(first_score_month, last_month, freq="M"):
        month_start = period.start_time
        month_end = period.end_time
        train_start = month_start - pd.Timedelta(days=180)
        train_mask = (scored["attempt_datetime"] >= train_start) & (scored["attempt_datetime"] < month_start)
        score_mask = (scored["attempt_datetime"] >= month_start) & (scored["attempt_datetime"] <= month_end)
        train = scored.loc[train_mask, MODEL_FEATURES].copy()
        current = scored.loc[score_mask, MODEL_FEATURES].copy()
        if len(train) < 500 or current.empty:
            continue
        medians = train.median(numeric_only=True)
        train = train.fillna(medians).fillna(0)
        current = current.fillna(medians).fillna(0)
        if len(train) > 50_000:
            train = train.sample(50_000, random_state=seed + period.month + period.year)
        model = IsolationForest(
            n_estimators=100,
            max_samples="auto",
            contamination=.02,
            random_state=seed + period.month + period.year,
            n_jobs=-1,
        )
        model.fit(train)
        raw = -model.decision_function(current)
        percentiles = pd.Series(raw).rank(method="average", pct=True).to_numpy() * 100
        scored.loc[score_mask, "anomaly_score"] = percentiles.round(2)
        scored.loc[score_mask, "model_version"] = f"IF-{period}"

    scored["risk_band"] = np.select(
        [scored["anomaly_score"] >= 98, scored["anomaly_score"] >= 93],
        ["high", "medium"],
        default="low",
    )
    scored.loc[scored["anomaly_score"].isna(), "risk_band"] = "warmup"
    scored["relationship_risk_score"] = np.minimum(
        100,
        np.where(scored["customers_collected_for_90d"] >= 3, 45, 0)
        + np.where(scored["authorization_customer_count"] >= 2, 45, 0)
        + np.where(scored["locations_30d"] > 2, 10, 0),
    )
    scored["priority_score"] = (
        scored["anomaly_score"].fillna(0) * .70 + scored["relationship_risk_score"] * .30
    ).round(2)
    reasons = scored.apply(_reason_codes, axis=1)
    scored["reason_1"] = reasons.str[0]
    scored["reason_2"] = reasons.str[1].fillna("")
    return scored

