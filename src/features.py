"""Time-aware behavioural features for explainable anomaly detection."""

from __future__ import annotations

from collections import Counter, defaultdict, deque

import numpy as np
import pandas as pd


def build_behavior_features(transactions: pd.DataFrame, prescriptions: pd.DataFrame) -> pd.DataFrame:
    tx = transactions.copy()
    tx["attempt_datetime"] = pd.to_datetime(tx["attempt_datetime"])
    rx = prescriptions[[
        "prescription_id", "authorization_id", "supply_days", "product_change_authorized"
    ]].copy()
    tx = tx.merge(rx, on="prescription_id", how="left", validate="one_to_one")
    tx = tx.sort_values(["attempt_datetime", "transaction_id"]).reset_index(drop=True)

    customer_30d = defaultdict(deque)
    collector_90d = defaultdict(deque)
    collector_counts = defaultdict(Counter)
    authorization_members = defaultdict(set)
    last_attempt = {}
    last_rejection = {}
    running_units_sum = defaultdict(float)
    running_units_count = defaultdict(int)
    prior_alerts_90d = defaultdict(deque)

    purchase_count_30d = np.zeros(len(tx), dtype=np.int16)
    locations_30d = np.zeros(len(tx), dtype=np.int16)
    days_since_previous = np.full(len(tx), np.nan)
    purchase_after_rejection = np.zeros(len(tx), dtype=np.int8)
    baseline_deviation = np.ones(len(tx), dtype=np.float32)
    collected_for_90d = np.zeros(len(tx), dtype=np.int16)
    authorization_customer_count = np.zeros(len(tx), dtype=np.int16)
    previous_alerts_90d = np.zeros(len(tx), dtype=np.int16)

    d30 = pd.Timedelta(days=30)
    d90 = pd.Timedelta(days=90)
    for idx, row in enumerate(tx.itertuples(index=False)):
        now = row.attempt_datetime
        customer = row.recipient_customer_id
        history = customer_30d[customer]
        while history and history[0][0] <= now - d30:
            history.popleft()
        purchase_count_30d[idx] = len(history) + 1
        locations_30d[idx] = len({item[1] for item in history}.union({row.location_id}))

        if customer in last_attempt:
            days_since_previous[idx] = (now - last_attempt[customer]).total_seconds() / 86400
        if customer in last_rejection and now - last_rejection[customer] <= d30:
            purchase_after_rejection[idx] = 1

        count = running_units_count[customer]
        if count:
            mean = running_units_sum[customer] / count
            baseline_deviation[idx] = float(row.normalized_units / max(mean, 1.0))

        collector = row.collector_customer_id
        collector_history = collector_90d[collector]
        counts = collector_counts[collector]
        while collector_history and collector_history[0][0] <= now - d90:
            _, old_recipient = collector_history.popleft()
            counts[old_recipient] -= 1
            if counts[old_recipient] <= 0:
                del counts[old_recipient]
        collector_history.append((now, customer))
        counts[customer] += 1
        collected_for_90d[idx] = len(counts)

        auth = row.authorization_id
        authorization_members[auth].add(customer)
        authorization_customer_count[idx] = len(authorization_members[auth])

        alert_history = prior_alerts_90d[customer]
        while alert_history and alert_history[0] <= now - d90:
            alert_history.popleft()
        previous_alerts_90d[idx] = len(alert_history)
        if bool(row.threshold_exceeded):
            alert_history.append(now)

        history.append((now, row.location_id))
        last_attempt[customer] = now
        if row.transaction_status == "rejected":
            last_rejection[customer] = now
        running_units_sum[customer] += float(row.normalized_units)
        running_units_count[customer] += 1

    tx["purchase_count_30d"] = purchase_count_30d
    tx["locations_30d"] = locations_30d
    tx["days_since_previous_purchase"] = days_since_previous
    tx["early_purchase"] = (
        tx["days_since_previous_purchase"].notna()
        & (tx["days_since_previous_purchase"] < tx["supply_days"] * .70)
    ).astype(int)
    tx["purchase_after_rejection"] = purchase_after_rejection
    tx["personal_baseline_deviation"] = baseline_deviation.round(3)
    tx["customers_collected_for_90d"] = collected_for_90d
    tx["authorization_customer_count"] = authorization_customer_count
    tx["previous_alerts_90d"] = previous_alerts_90d
    tx["near_threshold"] = tx["threshold_utilization"].between(.85, 1.0, inclusive="both").astype(int)
    tx["unauthorized_product_switch"] = (~tx["product_change_authorized"].fillna(True)).astype(int)
    tx["location_hopping"] = (tx["locations_30d"] > 2).astype(int)
    return tx

