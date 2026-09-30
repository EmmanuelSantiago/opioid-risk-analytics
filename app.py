"""Streamlit entry point for the portfolio application."""

from __future__ import annotations

import streamlit as st

from src.dashboard_data import load_dashboard_data
from src.dashboard_pages import (
    render_customer_behavior,
    render_financial,
    render_group_analysis,
    render_overview,
    render_product_trends,
    render_transaction_review,
)
from src.dashboard_style import APP_CSS

st.set_page_config(
    page_title="Opioid Dispensing Risk Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🛡️ Risk Analytics")
    st.caption("Controlled medication monitoring")
    page = st.radio(
        "Analysis",
        [
            "Risk overview",
            "Transaction review",
            "Customer behaviour",
            "Group analysis",
            "Molecule & brand",
            "Financial impact",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Threshold controls are deterministic. Anomaly scores prioritize review and never prove fraud.")

with st.spinner("Loading validated synthetic analytics…"):
    data = load_dashboard_data()

pages = {
    "Risk overview": render_overview,
    "Transaction review": render_transaction_review,
    "Customer behaviour": render_customer_behavior,
    "Group analysis": render_group_analysis,
    "Molecule & brand": render_product_trends,
    "Financial impact": render_financial,
}
pages[page](data)

