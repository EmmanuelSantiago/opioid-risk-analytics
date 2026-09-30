#!/usr/bin/env python3
"""Build anomaly scores, dashboard aggregates, and validation metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import ProjectConfig  # noqa: E402
from src.features import build_behavior_features  # noqa: E402
from src.model import score_monthly  # noqa: E402


def read(name: str, folder: str = "generated") -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / folder / f"{name}.csv.gz", low_memory=False)


def write(frame: pd.DataFrame, name: str) -> None:
    output = ROOT / "data" / "analytics"
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / f"{name}.csv.gz", index=False, compression="gzip")


def main():
    cfg = ProjectConfig()
    tx = read("dispensing_transactions")
    rx = read("prescriptions")
    claims = read("insurance_claims")
    alerts = read("threshold_alerts")
    products = read("products")
    molecules = read("molecules")
    customers = read("customers")
    truth = read("synthetic_truth", "validation")

    features = build_behavior_features(tx, rx)
    scored = score_monthly(features, cfg.seed)
    score_columns = [
        "transaction_id", "recipient_customer_id", "attempt_datetime", "anomaly_score",
        "risk_band", "relationship_risk_score", "priority_score", "reason_1", "reason_2",
        "model_version", "locations_30d", "purchase_count_30d", "days_since_previous_purchase",
        "customers_collected_for_90d", "authorization_customer_count",
    ]
    write(scored[score_columns], "anomaly_scores")

    claims["submitted_date"] = pd.to_datetime(claims["submitted_date"])
    tx["attempt_datetime"] = pd.to_datetime(tx["attempt_datetime"])
    tx["month"] = tx["attempt_datetime"].dt.to_period("M").astype(str)
    claims["month"] = claims["submitted_date"].dt.to_period("M").astype(str)
    monthly_tx = tx.groupby("month", as_index=False).agg(
        opioid_transactions=("transaction_id", "count"),
        units_requested=("normalized_units", "sum"),
        units_dispensed=("units_dispensed", "sum"),
        threshold_exceedances=("threshold_exceeded", "sum"),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    monthly_claims = claims.groupby("month", as_index=False).agg(
        claims=("claim_id", "count"),
        rejected_claims=("claim_status", lambda values: (values == "rejected").sum()),
        direct_product_loss=("direct_product_loss", "sum"),
        foregone_profit=("foregone_profit", "sum"),
        amount_billed=("amount_billed", "sum"),
    )
    monthly = monthly_tx.merge(monthly_claims, on="month", how="left")
    write(monthly, "monthly_kpis")

    product_map = products[["product_id", "product_name", "brand_name", "molecule_id"]]
    molecule_map = molecules[["molecule_id", "molecule_name"]]
    product_tx = tx.merge(product_map, on=["product_id", "molecule_id"], how="left").merge(molecule_map, on="molecule_id", how="left")
    molecule_summary = product_tx.groupby(["molecule_id", "molecule_name"], as_index=False).agg(
        transactions=("transaction_id", "count"),
        threshold_exceedances=("threshold_exceeded", "sum"),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    write(molecule_summary, "molecule_summary")

    insurer_tx = tx.merge(customers[["customer_id", "insurer_id"]], left_on="recipient_customer_id", right_on="customer_id", how="left")
    insurer_summary = insurer_tx.groupby("insurer_id", as_index=False).agg(
        transactions=("transaction_id", "count"),
        threshold_exceedances=("threshold_exceeded", "sum"),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    write(insurer_summary, "insurer_summary")

    truth_eval = truth.merge(scored[["transaction_id", "risk_band", "anomaly_score", "relationship_risk_score"]], on="transaction_id", how="left")
    truth_eval["detected_high_or_medium"] = truth_eval["risk_band"].isin(["high", "medium"])
    scenario_detection = truth_eval.groupby("scenario_type", as_index=False).agg(
        injected_transactions=("transaction_id", "count"),
        detected_high_or_medium=("detected_high_or_medium", "sum"),
        average_anomaly_score=("anomaly_score", "mean"),
        average_relationship_score=("relationship_risk_score", "mean"),
    )
    scenario_detection["detection_rate"] = (
        scenario_detection["detected_high_or_medium"] / scenario_detection["injected_transactions"]
    ).round(4)
    write(scenario_detection, "scenario_validation")

    valid_scores = scored[scored["risk_band"] != "warmup"]
    high_ids = set(valid_scores.loc[valid_scores["risk_band"] == "high", "transaction_id"])
    medium_ids = set(valid_scores.loc[valid_scores["risk_band"].isin(["high", "medium"]), "transaction_id"])
    truth_ids = set(truth["transaction_id"])
    cases = truth[truth["case_id"].fillna("") != ""]
    detected_cases = set(
        cases.loc[cases["transaction_id"].isin(set(valid_scores.loc[valid_scores["relationship_risk_score"] >= 45, "transaction_id"])), "case_id"]
    )
    metrics = {
        "scored_transactions": int(len(valid_scores)),
        "high_risk_transactions": int((valid_scores["risk_band"] == "high").sum()),
        "medium_risk_transactions": int((valid_scores["risk_band"] == "medium").sum()),
        "precision_top_2pct": round(len(high_ids & truth_ids) / max(len(high_ids), 1), 4),
        "recall_high_or_medium": round(len(medium_ids & truth_ids) / max(len(truth_ids), 1), 4),
        "coordinated_cases_detected": len(detected_cases),
        "coordinated_cases_total": int(cases["case_id"].nunique()),
    }
    analytics_dir = ROOT / "data" / "analytics"
    (analytics_dir / "model_validation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

