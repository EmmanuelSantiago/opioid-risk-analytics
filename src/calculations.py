"""Deterministic threshold and financial calculations."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FinancialImpact:
    direct_product_loss: float
    foregone_profit: float
    total_unpaid_exposure: float


def financial_impact(units: int, unit_cost: float, reimbursement_per_unit: float) -> FinancialImpact:
    direct = round(float(units) * float(unit_cost), 2)
    expected = round(float(units) * float(reimbursement_per_unit), 2)
    margin = round(expected - direct, 2)
    return FinancialImpact(direct, margin, expected)


def add_rolling_threshold_metrics(transactions: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    """Add prior/projected units and threshold status using past dispensed units only.

    A transaction exactly 30 days old is excluded, matching the approved rule.
    Rows must contain transaction_id, attempt_datetime, recipient_customer_id,
    molecule_id, normalized_units, units_dispensed, and maximum_units.
    """
    required = {
        "transaction_id", "attempt_datetime", "recipient_customer_id", "molecule_id",
        "normalized_units", "units_dispensed", "maximum_units",
    }
    missing = required.difference(transactions.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    result = transactions.copy()
    result["attempt_datetime"] = pd.to_datetime(result["attempt_datetime"])
    result = result.sort_values(["attempt_datetime", "transaction_id"]).reset_index(drop=True)

    history: dict[tuple[str, str], deque[tuple[pd.Timestamp, int]]] = defaultdict(deque)
    totals: dict[tuple[str, str], int] = defaultdict(int)
    prior_values = np.zeros(len(result), dtype=np.int32)
    projected_values = np.zeros(len(result), dtype=np.int32)

    delta = pd.Timedelta(days=window_days)
    for idx, row in enumerate(result.itertuples(index=False)):
        key = (row.recipient_customer_id, row.molecule_id)
        cutoff = row.attempt_datetime - delta
        queue = history[key]
        while queue and queue[0][0] <= cutoff:
            _, old_units = queue.popleft()
            totals[key] -= old_units

        prior = totals[key]
        requested = int(row.normalized_units)
        prior_values[idx] = prior
        projected_values[idx] = prior + requested

        dispensed = int(row.units_dispensed)
        if dispensed > 0:
            queue.append((row.attempt_datetime, dispensed))
            totals[key] += dispensed

    result["prior_30day_units"] = prior_values
    result["projected_30day_units"] = projected_values
    result["threshold_utilization"] = (
        result["projected_30day_units"] / result["maximum_units"]
    ).round(4)
    result["threshold_exceeded"] = result["projected_30day_units"] > result["maximum_units"]
    return result

