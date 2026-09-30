import unittest

import pandas as pd

from src.calculations import add_rolling_threshold_metrics, financial_impact


class CalculationTests(unittest.TestCase):
    def test_financial_impact(self):
        impact = financial_impact(10, 7.0, 10.0)
        self.assertEqual(impact.direct_product_loss, 70.0)
        self.assertEqual(impact.foregone_profit, 30.0)
        self.assertEqual(impact.total_unpaid_exposure, 100.0)

    def test_exactly_30_days_old_is_excluded(self):
        frame = pd.DataFrame({
            "transaction_id": ["T1", "T2", "T3", "T4"],
            "attempt_datetime": pd.to_datetime(["2025-06-10", "2025-06-25", "2025-06-30", "2025-07-10"]),
            "recipient_customer_id": ["C1"] * 4,
            "molecule_id": ["M1"] * 4,
            "normalized_units": [30] * 4,
            "units_dispensed": [30] * 4,
            "maximum_units": [90] * 4,
        })
        result = add_rolling_threshold_metrics(frame)
        july_10 = result.loc[result["transaction_id"] == "T4"].iloc[0]
        self.assertEqual(july_10["prior_30day_units"], 60)
        self.assertEqual(july_10["projected_30day_units"], 90)
        self.assertFalse(bool(july_10["threshold_exceeded"]))

    def test_rejected_units_do_not_enter_history(self):
        frame = pd.DataFrame({
            "transaction_id": ["T1", "T2", "T3"],
            "attempt_datetime": pd.to_datetime(["2025-06-01", "2025-06-05", "2025-06-08"]),
            "recipient_customer_id": ["C1"] * 3,
            "molecule_id": ["M1"] * 3,
            "normalized_units": [30, 30, 30],
            "units_dispensed": [30, 0, 30],
            "maximum_units": [60] * 3,
        })
        result = add_rolling_threshold_metrics(frame)
        third = result.loc[result["transaction_id"] == "T3"].iloc[0]
        self.assertEqual(third["prior_30day_units"], 30)
        self.assertEqual(third["projected_30day_units"], 60)


if __name__ == "__main__":
    unittest.main()

