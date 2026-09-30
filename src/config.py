"""Approved synthetic project assumptions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectConfig:
    seed: int = 20250929
    start_date: str = "2024-01-01"
    control_date: str = "2025-01-01"
    end_date: str = "2025-12-31"
    locations: int = 100
    cities: int = 25
    insurers: int = 6
    detailed_customers: int = 120_000
    represented_customers: int = 4_200_000
    daily_prescriptions: int = 10_100
    opioid_share: float = 0.05
    detailed_opioid_transactions: int = 365_000
    threshold_event_rate: float = 0.03
    approved_alert_share: float = 0.40
    anomaly_rate: float = 0.02
    coordinated_group_rate: float = 0.005
    investigation_cases: int = 40
    rolling_window_days: int = 30


MOLECULES = [
    ("MOL001", "Codeine", 90),
    ("MOL002", "Tramadol", 120),
    ("MOL003", "Hydrocodone", 60),
    ("MOL004", "Oxycodone", 60),
    ("MOL005", "Morphine", 90),
    ("MOL006", "Hydromorphone", 60),
    ("MOL007", "Fentanyl", 30),
    ("MOL008", "Buprenorphine", 60),
]

FICTIONAL_BRAND_STEMS = ["Arden", "Belaris", "Cenera", "Dovalis"]

