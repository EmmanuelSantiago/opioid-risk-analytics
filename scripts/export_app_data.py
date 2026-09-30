#!/usr/bin/env python3
"""Create compact, deployment-ready Parquet datasets for Streamlit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
ANALYTICS = ROOT / "data" / "analytics"
VALIDATION = ROOT / "data" / "validation"
OUTPUT = ROOT / "app_data"


def read(folder: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(folder / f"{name}.csv.gz", low_memory=False)


def main():
    OUTPUT.mkdir(exist_ok=True)
    tx = read(GENERATED, "dispensing_transactions")
    products = read(GENERATED, "products")
    molecules = read(GENERATED, "molecules")
    prescriptions = read(GENERATED, "prescriptions")
    alerts = read(GENERATED, "threshold_alerts")
    claims = read(GENERATED, "insurance_claims")
    customers = read(GENERATED, "customers")
    locations = read(GENERATED, "locations")
    cases = read(GENERATED, "investigation_cases")
    case_customers = read(GENERATED, "case_customers")
    scores = read(ANALYTICS, "anomaly_scores")
    truth = read(VALIDATION, "synthetic_truth")

    tx_columns = [
        "transaction_id", "recipient_customer_id", "collector_customer_id", "product_id",
        "molecule_id", "location_id", "prescription_id", "attempt_datetime", "normalized_units",
        "units_dispensed", "transaction_status", "control_period", "maximum_units",
        "prior_30day_units", "projected_30day_units", "threshold_utilization",
        "threshold_exceeded", "unit_cost_at_time", "reimbursement_at_time",
        "cost_protected", "margin_protected", "exposure_prevented",
    ]
    detail = tx[tx_columns].merge(
        products[["product_id", "product_name", "brand_name", "units_per_package"]], on="product_id", how="left"
    ).merge(
        molecules[["molecule_id", "molecule_name"]], on="molecule_id", how="left"
    ).merge(
        prescriptions[["prescription_id", "authorization_id", "prescriber_id", "supply_days", "product_change_authorized"]],
        on="prescription_id", how="left"
    ).merge(
        alerts[["transaction_id", "decision", "decision_reason"]], on="transaction_id", how="left"
    ).merge(
        claims[["transaction_id", "claim_status", "amount_billed", "amount_paid", "direct_product_loss", "foregone_profit", "settlement_days"]],
        on="transaction_id", how="left"
    ).merge(
        scores, on=["transaction_id", "recipient_customer_id", "attempt_datetime"], how="left"
    ).merge(
        customers[["customer_id", "insurer_id"]], left_on="recipient_customer_id", right_on="customer_id", how="left"
    ).merge(
        locations[["location_id", "location_name", "city_id", "region"]], on="location_id", how="left"
    )
    detail.drop(columns=["customer_id"], inplace=True)
    detail["attempt_datetime"] = pd.to_datetime(detail["attempt_datetime"])
    detail.to_parquet(OUTPUT / "transaction_detail.parquet", index=False, compression="zstd")

    case_truth = truth[truth["case_id"].fillna("") != ""][["transaction_id", "scenario_type", "case_id"]]
    case_detail = case_truth.merge(detail, on="transaction_id", how="left").merge(cases, on="case_id", how="left")
    case_detail.to_parquet(OUTPUT / "case_detail.parquet", index=False, compression="zstd")
    case_customers.to_parquet(OUTPUT / "case_customers.parquet", index=False, compression="zstd")

    detail["month"] = detail["attempt_datetime"].dt.to_period("M").astype(str)
    molecule_monthly = detail.groupby(["month", "molecule_id", "molecule_name"], as_index=False).agg(
        transactions=("transaction_id", "count"),
        alerts=("threshold_exceeded", "sum"),
        high_risk=("risk_band", lambda values: (values == "high").sum()),
        historical_loss=("direct_product_loss", "sum"),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    molecule_monthly.to_parquet(OUTPUT / "molecule_monthly.parquet", index=False, compression="zstd")

    location_summary = detail.groupby(["location_id", "location_name", "city_id", "region"], as_index=False).agg(
        transactions=("transaction_id", "count"),
        alerts=("threshold_exceeded", "sum"),
        high_risk=("risk_band", lambda values: (values == "high").sum()),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    location_summary.to_parquet(OUTPUT / "location_summary.parquet", index=False, compression="zstd")

    for source, name in [
        (ANALYTICS / "monthly_kpis.csv.gz", "monthly_kpis.csv.gz"),
        (ANALYTICS / "insurer_summary.csv.gz", "insurer_summary.csv.gz"),
        (ANALYTICS / "model_validation.json", "model_validation.json"),
        (GENERATED / "summary.json", "summary.json"),
    ]:
        shutil.copy2(source, OUTPUT / name)
    print(f"Created deployment data in {OUTPUT}")


if __name__ == "__main__":
    main()

