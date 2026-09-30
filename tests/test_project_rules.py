import unittest

from src.config import ProjectConfig


class ProjectRuleTests(unittest.TestCase):
    def test_approved_assumptions(self):
        cfg = ProjectConfig()
        self.assertEqual(cfg.rolling_window_days, 30)
        self.assertEqual(cfg.insurers, 6)
        self.assertEqual(cfg.locations, 100)
        self.assertAlmostEqual(cfg.opioid_share, 0.05)
        self.assertAlmostEqual(cfg.threshold_event_rate, 0.03)
        self.assertAlmostEqual(cfg.approved_alert_share, 0.40)


if __name__ == "__main__":
    unittest.main()

