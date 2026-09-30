#!/usr/bin/env python3
"""Generate the approved two-year synthetic portfolio dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.calculations import add_rolling_threshold_metrics  # noqa: E402
from src.config import FICTIONAL_BRAND_STEMS, MOLECULES, ProjectConfig  # noqa: E402


def identifiers(prefix: str, count: int, width: int = 7) -> np.ndarray:
    return np.array([f"{prefix}{i:0{width}d}" for i in range(1, count + 1)], dtype=object)


def write_csv(frame: pd.DataFrame, output_dir: Path, name: str) -> None:
    frame.to_csv(output_dir / f"{name}.csv.gz", index=False, compression="gzip")


def build_dimensions(cfg: ProjectConfig, rng: np.random.Generator, scale: float):
    customer_count = max(2_000, int(cfg.detailed_customers * scale))
    customer_ids = identifiers("CUS", customer_count)
    insurer_ids = identifiers("INS", cfg.insurers, 3)
    city_ids = identifiers("CITY", cfg.cities, 3)
    location_ids = identifiers("LOC", cfg.locations, 3)
    prescriber_count = max(300, int(2_500 * scale))
    prescriber_ids = identifiers("PRE", prescriber_count, 5)

    insurers = pd.DataFrame({
        "insurer_id": insurer_ids,
        "insurer_name": [f"Assurance Network {chr(65+i)}" for i in range(cfg.insurers)],
        "typical_payment_days": [35, 42, 48, 60, 75, 88],
    })
    locations = pd.DataFrame({
        "location_id": location_ids,
        "location_name": [f"Care Location {i:03d}" for i in range(1, cfg.locations + 1)],
        "city_id": np.resize(city_ids, cfg.locations),
        "region": np.resize(np.array(["North", "Central", "East", "West", "South"]), cfg.locations),
        "active_from": "2023-01-01",
        "active_to": "",
    })
    customers = pd.DataFrame({
        "customer_id": customer_ids,
        "insurer_id": rng.choice(insurer_ids, customer_count, p=[.24, .21, .18, .15, .13, .09]),
        "home_city_id": rng.choice(city_ids, customer_count),
        "customer_created_date": pd.to_datetime("2018-01-01") + pd.to_timedelta(rng.integers(0, 2190, customer_count), unit="D"),
        "monitoring_status": "normal",
        "active_flag": True,
    })
    prescribers = pd.DataFrame({
        "prescriber_id": prescriber_ids,
        "provider_type": rng.choice(["Physician", "Clinic"], prescriber_count, p=[.82, .18]),
        "city_id": rng.choice(city_ids, prescriber_count),
        "active_flag": True,
    })
    molecules = pd.DataFrame(MOLECULES, columns=["molecule_id", "molecule_name", "maximum_units"])
    molecules["regulated_flag"] = True
    molecules["active_flag"] = True
    thresholds = molecules[["molecule_id", "maximum_units"]].copy()
    thresholds.insert(0, "threshold_id", identifiers("THR", len(thresholds), 3))
    thresholds["window_days"] = cfg.rolling_window_days
    thresholds["effective_from"] = cfg.start_date
    thresholds["effective_to"] = ""
    thresholds["defined_by_role"] = "Pharmaceutical SME"
    thresholds["threshold_version"] = 1

    product_rows = []
    product_num = 1
    for molecule_id, molecule_name, _ in MOLECULES:
        for stem in FICTIONAL_BRAND_STEMS:
            units_per_package = int(rng.choice([10, 15, 30], p=[.25, .25, .50]))
            unit_cost = round(float(rng.uniform(0.65, 4.20)), 2)
            reimbursement = round(unit_cost * float(rng.uniform(1.18, 1.48)), 2)
            product_rows.append({
                "product_id": f"PRD{product_num:03d}",
                "product_name": f"{stem}{molecule_name[:3].lower()} {units_per_package}",
                "brand_name": f"{stem} Health",
                "molecule_id": molecule_id,
                "presentation": "Patch" if molecule_name == "Fentanyl" else rng.choice(["Tablet", "Capsule"]),
                "units_per_package": units_per_package,
                "unit_cost": unit_cost,
                "unit_reimbursement": reimbursement,
                "regulated_flag": True,
            })
            product_num += 1
    products = pd.DataFrame(product_rows)
    return customers, insurers, locations, prescribers, molecules, thresholds, products


def make_base_transactions(cfg, rng, scale, customers, locations, prescribers, products, thresholds):
    target = max(10_000, int(cfg.detailed_opioid_transactions * scale))
    dates = pd.to_datetime(cfg.start_date) + pd.to_timedelta(
        rng.integers(0, (pd.Timestamp(cfg.end_date) - pd.Timestamp(cfg.start_date)).days + 1, target), unit="D"
    ) + pd.to_timedelta(rng.integers(8 * 60, 20 * 60, target), unit="m")

    customer_ids = customers["customer_id"].to_numpy()
    normal_pool_start = min(len(customer_ids) // 5, 15_000)
    normal_pool = customer_ids[normal_pool_start:]
    chosen_customers = rng.choice(normal_pool, target)
    chosen_products = rng.choice(products["product_id"].to_numpy(), target)
    product_lookup = products.set_index("product_id")
    molecule_for_product = product_lookup.loc[chosen_products, "molecule_id"].to_numpy()
    units_per_package = product_lookup.loc[chosen_products, "units_per_package"].to_numpy(dtype=int)
    packages = rng.choice([1, 2], target, p=[.96, .04])
    normalized = packages * units_per_package

    transactions = pd.DataFrame({
        "transaction_id": identifiers("TXN", target, 8),
        "order_id": identifiers("ORD", target, 8),
        "prescription_id": identifiers("RX", target, 8),
        "recipient_customer_id": chosen_customers,
        "collector_customer_id": chosen_customers.copy(),
        "product_id": chosen_products,
        "molecule_id": molecule_for_product,
        "location_id": rng.choice(locations["location_id"].to_numpy(), target),
        "attempt_datetime": dates,
        "packages_requested": packages,
        "normalized_units": normalized,
        "units_dispensed": normalized.copy(),
        "transaction_status": "dispensed",
        "control_period": np.where(dates < pd.Timestamp(cfg.control_date), "historical", "control_active"),
    })
    transactions["maximum_units"] = transactions["molecule_id"].map(
        thresholds.set_index("molecule_id")["maximum_units"]
    ).astype(int)
    transactions["unit_cost_at_time"] = product_lookup.loc[chosen_products, "unit_cost"].to_numpy() * rng.uniform(.97, 1.04, target)
    transactions["reimbursement_at_time"] = product_lookup.loc[chosen_products, "unit_reimbursement"].to_numpy() * rng.uniform(.98, 1.05, target)
    transactions["unit_cost_at_time"] = transactions["unit_cost_at_time"].round(2)
    transactions["reimbursement_at_time"] = transactions["reimbursement_at_time"].round(2)

    prescriptions = pd.DataFrame({
        "prescription_id": transactions["prescription_id"],
        "authorization_id": identifiers("AUT", target, 8),
        "recipient_customer_id": transactions["recipient_customer_id"],
        "prescriber_id": rng.choice(prescribers["prescriber_id"].to_numpy(), target),
        "issued_date": pd.to_datetime(transactions["attempt_datetime"]).dt.normalize() - pd.to_timedelta(rng.integers(0, 5, target), unit="D"),
        "supply_days": rng.choice([10, 15, 30], target, p=[.18, .22, .60]),
        "valid_until": pd.to_datetime(transactions["attempt_datetime"]).dt.normalize() + pd.to_timedelta(30, unit="D"),
        "prescription_status": "completed",
        "product_change_authorized": True,
    })
    return transactions, prescriptions


def inject_threshold_sequences(cfg, rng, scale, transactions, prescriptions, customers, locations, products, thresholds):
    target_events = max(300, int(cfg.detailed_opioid_transactions * cfg.threshold_event_rate * scale))
    per_period = target_events // 2
    reserved_customers = customers["customer_id"].to_numpy()[: target_events + 100]
    product_lookup = products.set_index("product_id")
    products_by_molecule = {m: group["product_id"].to_numpy() for m, group in products.groupby("molecule_id")}
    threshold_lookup = thresholds.set_index("molecule_id")["maximum_units"].to_dict()
    rows = []
    rx_rows = []
    truth = []
    sequence_ids = []
    next_id = len(transactions) + 1
    event_no = 0
    for period, start, end in [
        ("historical", pd.Timestamp("2024-02-01"), pd.Timestamp("2024-12-15")),
        ("control_active", pd.Timestamp("2025-02-01"), pd.Timestamp("2025-12-15")),
    ]:
        for _ in range(per_period):
            customer_id = reserved_customers[event_no]
            molecule_id, _, max_units = MOLECULES[event_no % len(MOLECULES)]
            product_id = str(rng.choice(products_by_molecule[molecule_id]))
            units_per_package = int(product_lookup.loc[product_id, "units_per_package"])
            packages = 1
            units = units_per_package
            prior_count = int(np.ceil(max_units / units))
            anchor = start + pd.to_timedelta(int(rng.integers(0, (end - start).days + 1)), unit="D")
            offsets = np.linspace(26, 2, prior_count, dtype=int).tolist() + [0]
            for step, offset in enumerate(offsets):
                attempt = anchor - pd.Timedelta(days=int(offset)) + pd.Timedelta(hours=10 + step)
                tx_id = f"TXN{next_id:08d}"
                rx_id = f"RX{next_id:08d}"
                auth_id = f"AUT{next_id:08d}"
                cost = round(float(product_lookup.loc[product_id, "unit_cost"]) * float(rng.uniform(.98, 1.03)), 2)
                reimb = round(float(product_lookup.loc[product_id, "unit_reimbursement"]) * float(rng.uniform(.99, 1.04)), 2)
                rows.append({
                    "transaction_id": tx_id,
                    "order_id": f"ORD{next_id:08d}",
                    "prescription_id": rx_id,
                    "recipient_customer_id": customer_id,
                    "collector_customer_id": customer_id,
                    "product_id": product_id,
                    "molecule_id": molecule_id,
                    "location_id": str(rng.choice(locations["location_id"].to_numpy())),
                    "attempt_datetime": attempt,
                    "packages_requested": packages,
                    "normalized_units": units,
                    "units_dispensed": units,
                    "transaction_status": "dispensed",
                    "control_period": period,
                    "maximum_units": max_units,
                    "unit_cost_at_time": cost,
                    "reimbursement_at_time": reimb,
                })
                sequence_ids.append(tx_id)
                rx_rows.append({
                    "prescription_id": rx_id,
                    "authorization_id": auth_id,
                    "recipient_customer_id": customer_id,
                    "prescriber_id": str(rng.choice(prescriptions["prescriber_id"].to_numpy())),
                    "issued_date": attempt.normalize() - pd.Timedelta(days=1),
                    "supply_days": int(rng.choice([10, 15, 30], p=[.2, .2, .6])),
                    "valid_until": attempt.normalize() + pd.Timedelta(days=30),
                    "prescription_status": "completed",
                    "product_change_authorized": True,
                })
                if step == len(offsets) - 1:
                    truth.append({"transaction_id": tx_id, "scenario_type": "threshold_exceedance", "case_id": ""})
                next_id += 1
            event_no += 1
    combined_tx = pd.concat([transactions, pd.DataFrame(rows)], ignore_index=True)
    combined_rx = pd.concat([prescriptions, pd.DataFrame(rx_rows)], ignore_index=True)
    return combined_tx, combined_rx, pd.DataFrame(truth), set(sequence_ids)


def trim_to_approved_volume(cfg, rng, scale, transactions, prescriptions, truth, protected_sequence_ids):
    """Keep the approved detailed volume after injecting required sequences."""
    target = max(10_000, int(cfg.detailed_opioid_transactions * scale))
    excess = len(transactions) - target
    if excess <= 0:
        return transactions, prescriptions
    protected = set(truth["transaction_id"]).union(protected_sequence_ids)
    removable = transactions.loc[~transactions["transaction_id"].isin(protected), "transaction_id"].to_numpy()
    drop_ids = set(rng.choice(removable, size=excess, replace=False))
    kept_transactions = transactions[~transactions["transaction_id"].isin(drop_ids)].copy()
    kept_rx_ids = set(kept_transactions["prescription_id"])
    kept_prescriptions = prescriptions[prescriptions["prescription_id"].isin(kept_rx_ids)].copy()
    return kept_transactions, kept_prescriptions


def inject_behavioural_scenarios(cfg, rng, scale, transactions, prescriptions, truth, customers):
    eligible = transactions[
        ~transactions["transaction_id"].isin(truth["transaction_id"])
    ].sample(n=max(200, int(cfg.detailed_opioid_transactions * cfg.anomaly_rate * scale)), random_state=cfg.seed)
    scenario_names = np.resize(np.array([
        "location_hopping", "early_refill", "near_threshold_pattern", "personal_baseline_change",
        "unauthorized_product_switch", "sustained_elevated_activity",
    ]), len(eligible))
    anomaly_truth = pd.DataFrame({
        "transaction_id": eligible["transaction_id"].to_numpy(),
        "scenario_type": scenario_names,
        "case_id": "",
    })

    tx = transactions.copy()
    rx = prescriptions.copy()
    location_ids = tx["location_id"].unique()
    customer_ids = customers["customer_id"].to_numpy()
    index_map = pd.Series(tx.index, index=tx["transaction_id"]).to_dict()
    rx_index_map = pd.Series(rx.index, index=rx["prescription_id"]).to_dict()
    for transaction_id, scenario in zip(anomaly_truth["transaction_id"], scenario_names):
        idx = index_map[transaction_id]
        if scenario == "location_hopping":
            tx.at[idx, "location_id"] = str(rng.choice(location_ids))
        elif scenario == "early_refill":
            rx_idx = rx_index_map[tx.at[idx, "prescription_id"]]
            rx.at[rx_idx, "supply_days"] = 30
        elif scenario == "near_threshold_pattern":
            tx.at[idx, "normalized_units"] = max(1, int(tx.at[idx, "maximum_units"] * .90))
            tx.at[idx, "units_dispensed"] = tx.at[idx, "normalized_units"]
        elif scenario == "personal_baseline_change":
            tx.at[idx, "packages_requested"] = 2
            tx.at[idx, "normalized_units"] = min(tx.at[idx, "maximum_units"], tx.at[idx, "normalized_units"] * 2)
            tx.at[idx, "units_dispensed"] = tx.at[idx, "normalized_units"]
        elif scenario == "unauthorized_product_switch":
            rx_idx = rx_index_map[tx.at[idx, "prescription_id"]]
            rx.at[rx_idx, "product_change_authorized"] = False
        elif scenario == "sustained_elevated_activity":
            tx.at[idx, "normalized_units"] = max(1, int(tx.at[idx, "maximum_units"] * .80))
            tx.at[idx, "units_dispensed"] = tx.at[idx, "normalized_units"]

    group_target = max(100, int(cfg.detailed_opioid_transactions * cfg.coordinated_group_rate * scale))
    group_candidates = tx.sample(n=min(group_target, len(tx)), random_state=cfg.seed + 1)
    cases = []
    case_customers = []
    group_truth = []
    group_indices = np.array_split(group_candidates.index.to_numpy(), cfg.investigation_cases)
    for case_num, indices in enumerate(group_indices, start=1):
        case_id = f"CASE{case_num:03d}"
        collector_id = str(rng.choice(customer_ids[: max(500, len(customer_ids)//10)]))
        shared_auth = f"SHARED-AUTH-{case_num:03d}"
        case_type = "shared_collector" if case_num % 2 else "authorization_reuse"
        cases.append({
            "case_id": case_id,
            "opened_date": "2025-06-01",
            "case_status": rng.choice(["open", "monitoring", "closed"], p=[.25, .50, .25]),
            "case_category": case_type,
            "outcome": rng.choice(["suspicious", "escalated", "inconclusive"], p=[.50, .30, .20]),
            "closed_date": "" if case_num % 4 else "2025-12-15",
        })
        members = set()
        for idx in indices:
            tx.at[idx, "collector_customer_id"] = collector_id
            rx_idx = rx_index_map[tx.at[idx, "prescription_id"]]
            if case_type == "authorization_reuse":
                rx.at[rx_idx, "authorization_id"] = shared_auth
            member = tx.at[idx, "recipient_customer_id"]
            members.add(member)
            group_truth.append({"transaction_id": tx.at[idx, "transaction_id"], "scenario_type": case_type, "case_id": case_id})
        for member in members:
            case_customers.append({"case_id": case_id, "customer_id": member})

    all_truth = pd.concat([truth, anomaly_truth, pd.DataFrame(group_truth)], ignore_index=True)
    return tx, rx, pd.DataFrame(cases), pd.DataFrame(case_customers), all_truth


def apply_controls_and_build_facts(cfg, rng, transactions, prescriptions, customers):
    calculated = add_rolling_threshold_metrics(transactions, cfg.rolling_window_days)
    control_alert_mask = (calculated["control_period"] == "control_active") & calculated["threshold_exceeded"]
    alert_indices = calculated.index[control_alert_mask].to_numpy()
    rng.shuffle(alert_indices)
    approved_count = int(round(len(alert_indices) * cfg.approved_alert_share))
    approved_indices = set(alert_indices[:approved_count])
    rejected_indices = set(alert_indices[approved_count:])

    calculated["alert_decision"] = ""
    if approved_indices:
        calculated.loc[list(approved_indices), "alert_decision"] = "approved"
    if rejected_indices:
        calculated.loc[list(rejected_indices), "alert_decision"] = "rejected"
        calculated.loc[list(rejected_indices), "units_dispensed"] = 0
        calculated.loc[list(rejected_indices), "transaction_status"] = "rejected"

    calculated = add_rolling_threshold_metrics(calculated.drop(columns=[
        "prior_30day_units", "projected_30day_units", "threshold_utilization", "threshold_exceeded"
    ]), cfg.rolling_window_days)
    final_alert_mask = (calculated["control_period"] == "control_active") & calculated["threshold_exceeded"]
    missing_decision = final_alert_mask & (calculated["alert_decision"] == "")
    calculated.loc[missing_decision, "alert_decision"] = rng.choice(
        ["approved", "rejected"], missing_decision.sum(), p=[cfg.approved_alert_share, 1-cfg.approved_alert_share]
    )
    newly_rejected = missing_decision & (calculated["alert_decision"] == "rejected")
    calculated.loc[newly_rejected, "units_dispensed"] = 0
    calculated.loc[newly_rejected, "transaction_status"] = "rejected"

    alerts_src = calculated[final_alert_mask].copy()
    alerts = pd.DataFrame({
        "alert_id": identifiers("ALT", len(alerts_src), 7),
        "transaction_id": alerts_src["transaction_id"].to_numpy(),
        "created_datetime": alerts_src["attempt_datetime"].to_numpy(),
        "molecule_id": alerts_src["molecule_id"].to_numpy(),
        "prior_30day_units": alerts_src["prior_30day_units"].to_numpy(),
        "requested_units": alerts_src["normalized_units"].to_numpy(),
        "projected_units": alerts_src["projected_30day_units"].to_numpy(),
        "maximum_units": alerts_src["maximum_units"].to_numpy(),
        "decision": alerts_src["alert_decision"].to_numpy(),
        "decision_datetime": pd.to_datetime(alerts_src["attempt_datetime"]) + pd.to_timedelta(rng.integers(5, 240, len(alerts_src)), unit="m"),
        "decision_reason": np.where(alerts_src["alert_decision"].to_numpy() == "approved", "valid_exception", "insufficient_authorization"),
        "case_id": "",
    })

    customer_insurer = customers.set_index("customer_id")["insurer_id"]
    dispensed = calculated[calculated["units_dispensed"] > 0].copy()
    historical_rejected = (dispensed["control_period"] == "historical") & dispensed["threshold_exceeded"]
    claim_status = np.where(historical_rejected, "rejected", "paid")
    submit_dates = pd.to_datetime(dispensed["attempt_datetime"]).dt.normalize() + pd.to_timedelta(rng.integers(0, 4, len(dispensed)), unit="D")
    settlement_days = rng.integers(30, 91, len(dispensed))
    billed = (dispensed["units_dispensed"] * dispensed["reimbursement_at_time"]).round(2)
    product_cost = (dispensed["units_dispensed"] * dispensed["unit_cost_at_time"]).round(2)
    claims = pd.DataFrame({
        "claim_id": identifiers("CLM", len(dispensed), 8),
        "transaction_id": dispensed["transaction_id"].to_numpy(),
        "insurer_id": dispensed["recipient_customer_id"].map(customer_insurer).to_numpy(),
        "submitted_date": submit_dates.to_numpy(),
        "settlement_date": (submit_dates + pd.to_timedelta(settlement_days, unit="D")).to_numpy(),
        "claim_status": claim_status,
        "amount_billed": billed.to_numpy(),
        "amount_paid": np.where(claim_status == "paid", billed, 0.0),
        "direct_product_loss": np.where(claim_status == "rejected", product_cost, 0.0),
        "foregone_profit": np.where(claim_status == "rejected", billed - product_cost, 0.0),
        "settlement_days": settlement_days,
    })

    rejected_control = calculated[(calculated["control_period"] == "control_active") & (calculated["alert_decision"] == "rejected")]
    calculated["cost_protected"] = 0.0
    calculated["margin_protected"] = 0.0
    calculated["exposure_prevented"] = 0.0
    calculated.loc[rejected_control.index, "cost_protected"] = (
        rejected_control["normalized_units"] * rejected_control["unit_cost_at_time"]
    ).round(2)
    calculated.loc[rejected_control.index, "margin_protected"] = (
        rejected_control["normalized_units"] * (rejected_control["reimbursement_at_time"] - rejected_control["unit_cost_at_time"])
    ).round(2)
    calculated.loc[rejected_control.index, "exposure_prevented"] = (
        rejected_control["normalized_units"] * rejected_control["reimbursement_at_time"]
    ).round(2)
    return calculated, alerts, claims


def build_daily_volume(cfg, rng):
    dates = pd.date_range(cfg.start_date, cfg.end_date, freq="D")
    locations = identifiers("LOC", cfg.locations, 3)
    grid = pd.MultiIndex.from_product([dates, locations], names=["date", "location_id"]).to_frame(index=False)
    base = cfg.daily_prescriptions / cfg.locations
    weekday_factor = np.where(grid["date"].dt.dayofweek < 5, 1.08, .80)
    grid["total_prescriptions"] = np.maximum(10, rng.normal(base * weekday_factor, 12)).round().astype(int)
    grid["opioid_prescriptions"] = rng.binomial(grid["total_prescriptions"], cfg.opioid_share)
    grid["total_claim_value"] = (grid["total_prescriptions"] * rng.uniform(38, 74, len(grid))).round(2)
    return grid


def validate_and_summarize(cfg, transactions, alerts, claims, daily, truth):
    rejected_tx = transactions[transactions["transaction_status"] == "rejected"]
    claim_tx_ids = set(claims["transaction_id"])
    checks = {
        "no_year1_threshold_alerts": bool((pd.to_datetime(alerts["created_datetime"]) >= pd.Timestamp(cfg.control_date)).all()),
        "rejected_transactions_have_zero_dispensed": bool((rejected_tx["units_dispensed"] == 0).all()),
        "rejected_transactions_have_no_claim": bool(set(rejected_tx["transaction_id"]).isdisjoint(claim_tx_ids)),
        "approved_alerts_are_dispensed": bool((transactions.loc[transactions["alert_decision"] == "approved", "units_dispensed"] > 0).all()),
        "claims_only_paid_or_rejected": bool(set(claims["claim_status"]).issubset({"paid", "rejected"})),
        "settlement_between_30_and_90_days": bool(claims["settlement_days"].between(30, 90).all()),
        "all_financial_values_nonnegative": bool((claims[["amount_billed", "amount_paid", "direct_product_loss", "foregone_profit"]] >= 0).all().all()),
    }
    summary = {
        "represented_customer_population": cfg.represented_customers,
        "represented_prescriptions": int(daily["total_prescriptions"].sum()),
        "detailed_opioid_transactions": int(len(transactions)),
        "detailed_customers": int(transactions["recipient_customer_id"].nunique()),
        "threshold_alerts": int(len(alerts)),
        "approved_alerts": int((alerts["decision"] == "approved").sum()),
        "rejected_alerts": int((alerts["decision"] == "rejected").sum()),
        "historical_rejected_claims": int((claims["claim_status"] == "rejected").sum()),
        "historical_direct_product_loss": round(float(claims["direct_product_loss"].sum()), 2),
        "historical_foregone_profit": round(float(claims["foregone_profit"].sum()), 2),
        "historical_unpaid_exposure": round(float(claims.loc[claims["claim_status"] == "rejected", "amount_billed"].sum()), 2),
        "exposure_prevented": round(float(transactions["exposure_prevented"].sum()), 2),
        "synthetic_truth_records": int(len(truth)),
        "validation_checks": checks,
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"Validation failed: {failed}")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1.0, help="Scale detailed synthetic facts; dimensions retain useful minimums.")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "generated")
    args = parser.parse_args()
    cfg = ProjectConfig()
    rng = np.random.default_rng(cfg.seed)
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    validation_dir = ROOT / "data" / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)

    customers, insurers, locations, prescribers, molecules, thresholds, products = build_dimensions(cfg, rng, args.scale)
    transactions, prescriptions = make_base_transactions(cfg, rng, args.scale, customers, locations, prescribers, products, thresholds)
    transactions, prescriptions, truth, sequence_ids = inject_threshold_sequences(
        cfg, rng, args.scale, transactions, prescriptions, customers, locations, products, thresholds
    )
    transactions, prescriptions = trim_to_approved_volume(
        cfg, rng, args.scale, transactions, prescriptions, truth, sequence_ids
    )
    transactions, prescriptions, cases, case_customers, truth = inject_behavioural_scenarios(
        cfg, rng, args.scale, transactions, prescriptions, truth, customers
    )
    transactions, alerts, claims = apply_controls_and_build_facts(cfg, rng, transactions, prescriptions, customers)
    daily = build_daily_volume(cfg, rng)
    summary = validate_and_summarize(cfg, transactions, alerts, claims, daily, truth)

    for frame, name in [
        (customers, "customers"), (insurers, "insurers"), (locations, "locations"),
        (prescribers, "prescribers"), (molecules, "molecules"), (thresholds, "molecule_thresholds"),
        (products, "products"), (prescriptions, "prescriptions"),
        (transactions, "dispensing_transactions"), (alerts, "threshold_alerts"),
        (claims, "insurance_claims"), (cases, "investigation_cases"),
        (case_customers, "case_customers"), (daily, "daily_network_volume"),
    ]:
        write_csv(frame, output_dir, name)
    write_csv(truth, validation_dir, "synthetic_truth")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
