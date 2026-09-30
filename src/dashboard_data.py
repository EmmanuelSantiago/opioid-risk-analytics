"""Cached data access for the Streamlit application."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app_data"


@st.cache_data(show_spinner=False)
def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_parquet(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / name)


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def load_dashboard_data() -> dict:
    return {
        "summary": load_json("summary.json"),
        "validation": load_json("model_validation.json"),
        "transactions": load_parquet("transaction_detail.parquet"),
        "cases": load_parquet("case_detail.parquet"),
        "case_customers": load_parquet("case_customers.parquet"),
        "molecule_monthly": load_parquet("molecule_monthly.parquet"),
        "location_summary": load_parquet("location_summary.parquet"),
        "monthly": load_csv("monthly_kpis.csv.gz"),
        "insurer_summary": load_csv("insurer_summary.csv.gz"),
    }

