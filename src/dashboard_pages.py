"""Six approved Streamlit dashboard pages."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard_style import PLOTLY_LAYOUT

BRAND = "#4eb8cc"
GOOD = "#3dcea0"
RISK = "#ef7a6a"
WARN = "#e3b15a"
MUTED = "#93a8bb"


def money(value: float) -> str:
    return f"${value:,.0f}"


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f"# {title}")
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


DATE_TICKS = [
    {"dtickrange": [None, 60_000], "value": "%H:%M:%S"},
    {"dtickrange": [60_000, 86_400_000], "value": "%b %d %H:%M"},
    {"dtickrange": [86_400_000, "M1"], "value": "%b %d"},
    {"dtickrange": ["M1", None], "value": "%b %Y"},
]


def style_figure(fig: go.Figure, title: str, height: int = 440) -> go.Figure:
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title={"text": title, "font": {"color": "#e6eef6", "size": 16}, "x": 0, "xanchor": "left"},
        height=height,
    )
    shared = {
        "tickfont": {"color": "#93a8bb"},
        "title_font": {"color": "#c5d4e0", "size": 13},
        "automargin": True,
        "title_standoff": 14,
    }
    fig.update_xaxes(showgrid=False, linecolor="#2c3d50", nticks=6, **shared)
    fig.update_yaxes(gridcolor="#243446", zeroline=False, nticks=6, **shared)
    return fig


def show_figure(fig: go.Figure, title: str, height: int = 440) -> None:
    st.plotly_chart(style_figure(fig, title, height), width="stretch", config={"displayModeBar": False})


def risk_label(value: str) -> str:
    css = {"high": "risk-high", "medium": "risk-medium", "low": "risk-low"}.get(value, "")
    return f'<span class="{css}">{value.title()}</span>'


def render_overview(data: dict) -> None:
    page_header("Risk overview", "From delayed insurance losses to pre-dispensing prevention")
    st.markdown('<div class="synthetic-note"><strong>Synthetic case study.</strong> All customers, products, thresholds, cases and financial results are generated for portfolio demonstration.</div>', unsafe_allow_html=True)
    summary = data["summary"]
    validation = data["validation"]
    cols = st.columns(4)
    cols[0].metric("Prescriptions represented", f"{summary['represented_prescriptions']/1_000_000:.2f}M")
    cols[1].metric("Threshold alerts", f"{summary['threshold_alerts']:,}", "40% approved · 60% rejected")
    cols[2].metric("Historical unpaid exposure", money(summary["historical_unpaid_exposure"]))
    cols[3].metric("Exposure prevented", money(summary["exposure_prevented"]))

    monthly = data["monthly"].copy()
    monthly["month"] = pd.to_datetime(monthly["month"])
    monthly["historical_unpaid_exposure"] = monthly["direct_product_loss"].fillna(0) + monthly["foregone_profit"].fillna(0)
    chart_data = monthly.melt(
        id_vars="month",
        value_vars=["historical_unpaid_exposure", "exposure_prevented"],
        var_name="measure",
        value_name="value",
    )
    chart_data["measure"] = chart_data["measure"].map({
        "historical_unpaid_exposure": "Historical unpaid exposure",
        "exposure_prevented": "Exposure prevented",
    })
    left, right = st.columns([1.45, 1])
    with left.container(border=True):
        fig = px.area(
            chart_data, x="month", y="value", color="measure",
            color_discrete_map={"Historical unpaid exposure": RISK, "Exposure prevented": GOOD},
            labels={"month": "Month", "value": "Amount", "measure": "Measure"},
        )
        fig.update_traces(line_width=2, fill="tonexty")
        fig.update_yaxes(tickprefix="$", tickformat=",")
        show_figure(fig, "Loss discovered vs exposure prevented")
    with right.container(border=True):
        st.subheader("Investigation priorities")
        top = data["transactions"].query("risk_band == 'high'").nlargest(6, "priority_score")
        display = top[["transaction_id", "reason_1", "reason_2", "priority_score"]].copy()
        display.columns = ["Transaction", "Primary reason", "Secondary reason", "Priority"]
        st.dataframe(display, hide_index=True, width="stretch", height=322)

    st.subheader("Control and model performance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Top-2% precision", f"{validation['precision_top_2pct']:.1%}")
    c2.metric("High + medium recall", f"{validation['recall_high_or_medium']:.1%}")
    c3.metric("Coordinated cases recovered", f"{validation['coordinated_cases_detected']}/{validation['coordinated_cases_total']}")
    c4.metric("Detailed opioid transactions", f"{summary['detailed_opioid_transactions']:,}")


def render_transaction_review(data: dict) -> None:
    page_header("Transaction review", "Reconstruct one rolling 30-day dispensing decision")
    tx = data["transactions"]
    candidates = tx[tx["threshold_exceeded"] == True].copy()  # noqa: E712
    candidates = candidates.sort_values("attempt_datetime", ascending=False).head(2000)
    selected_id = st.selectbox(
        "Select an alert transaction",
        candidates["transaction_id"].tolist(),
        format_func=lambda value: _format_transaction(candidates, value),
    )
    row = candidates.loc[candidates["transaction_id"] == selected_id].iloc[0]
    cols = st.columns(5)
    cols[0].metric("Molecule", row["molecule_name"])
    cols[1].metric("Prior 30-day units", f"{int(row['prior_30day_units'])}")
    cols[2].metric("Requested units", f"{int(row['normalized_units'])}")
    cols[3].metric("Projected units", f"{int(row['projected_30day_units'])}")
    cols[4].metric("Threshold", f"{int(row['maximum_units'])}")

    decision = row["decision"] if pd.notna(row["decision"]) else "Historical—no control"
    message = (
        f"The purchase projected <strong>{int(row['projected_30day_units'])} units</strong>, "
        f"exceeding the {int(row['maximum_units'])}-unit limit. "
        f"Decision: <strong>{str(decision).title()}</strong>."
    )
    st.markdown(f'<div class="decision-box">{message}</div>', unsafe_allow_html=True)

    attempt = pd.Timestamp(row["attempt_datetime"])
    history = tx[
        (tx["recipient_customer_id"] == row["recipient_customer_id"])
        & (tx["molecule_id"] == row["molecule_id"])
        & (tx["attempt_datetime"] > attempt - pd.Timedelta(days=30))
        & (tx["attempt_datetime"] <= attempt)
    ].sort_values("attempt_datetime").copy()
    history["cumulative_dispensed"] = history["units_dispensed"].cumsum()
    left, right = st.columns([1.45, 1])
    with left.container(border=True):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history["attempt_datetime"], y=history["cumulative_dispensed"], mode="lines+markers",
            name="Cumulative dispensed", line={"color": BRAND, "width": 3}, marker={"size": 8},
            customdata=history[["location_name", "normalized_units"]],
            hovertemplate="%{x|%b %d}<br>Cumulative: %{y} units<br>Location: %{customdata[0]}<br>Requested: %{customdata[1]}<extra></extra>",
        ))
        fig.update_xaxes(title="Date", tickformatstops=DATE_TICKS)
        fig.update_yaxes(title="Cumulative units")
        fig.add_hline(
            y=row["maximum_units"], line_dash="dash", line_color=RISK,
            annotation_text="Threshold", annotation_position="bottom right",
            annotation_font_color=RISK,
        )
        show_figure(fig, "Customer + molecule history across all locations")
    with right.container(border=True):
        st.subheader("Decision context")
        st.markdown(f"**Product:** {row['product_name']}")
        st.markdown(f"**Brand:** {row['brand_name']}")
        st.markdown(f"**Supply duration:** {int(row['supply_days'])} days")
        st.markdown(f"**Location:** {row['location_name']}")
        st.markdown(f"**Collector differs from recipient:** {'Yes' if row['collector_customer_id'] != row['recipient_customer_id'] else 'No'}")
        st.markdown(f"**Claim created:** {'Yes' if pd.notna(row['claim_status']) else 'No'}")
        if pd.notna(row["decision_reason"]):
            st.markdown(f"**Decision reason:** {str(row['decision_reason']).replace('_', ' ').title()}")


def _format_transaction(candidates: pd.DataFrame, value: str) -> str:
    row = candidates.loc[candidates["transaction_id"] == value].iloc[0]
    date = pd.Timestamp(row["attempt_datetime"]).strftime("%Y-%m-%d")
    decision = str(row["decision"]).title() if pd.notna(row["decision"]) else "Historical"
    return f"{value} · {date} · {row['molecule_name']} · {decision}"


def render_customer_behavior(data: dict) -> None:
    page_header("Customer behaviour", "Explain unusual activity relative to personal history and treatment duration")
    tx = data["transactions"]
    ranked = tx[tx["risk_band"].isin(["high", "medium"])].sort_values("priority_score", ascending=False)
    customer_ids = ranked["recipient_customer_id"].drop_duplicates().head(1000).tolist()
    selected = st.selectbox("Select a prioritized customer", customer_ids)
    history = tx[tx["recipient_customer_id"] == selected].sort_values("attempt_datetime").copy()
    history["Risk"] = history["risk_band"].astype(str).str.title()
    latest = history.loc[history["priority_score"].idxmax()]
    cols = st.columns(4)
    cols[0].metric("Highest anomaly score", f"{latest['anomaly_score']:.1f}")
    cols[1].metric("Risk band", str(latest["risk_band"]).title())
    cols[2].metric("Locations used", f"{history['location_id'].nunique()}")
    cols[3].metric("Threshold alerts", f"{int(history['threshold_exceeded'].sum())}")
    st.markdown(
        f'<span class="reason-pill">{latest["reason_1"]}</span>'
        + (f'<span class="reason-pill">{latest["reason_2"]}</span>' if latest["reason_2"] else ""),
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.35, 1])
    with left.container(border=True):
        fig = px.scatter(
            history, x="attempt_datetime", y="normalized_units", color="molecule_name",
            size="priority_score", size_max=16,
            custom_data=["product_name", "location_name", "reason_1", "Risk", "priority_score"],
            labels={
                "attempt_datetime": "Date",
                "normalized_units": "Units",
                "molecule_name": "Molecule",
                "priority_score": "Priority",
            },
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Date: %{x|%b %d, %Y}<br>"
                "Units: %{y}<br>"
                "Product: %{customdata[0]}<br>"
                "Location: %{customdata[1]}<br>"
                "Reason: %{customdata[2]}<br>"
                "Risk: %{customdata[3]}<br>"
                "Priority: %{customdata[4]:.0f}"
                "<extra></extra>"
            )
        )
        fig.update_xaxes(tickformatstops=DATE_TICKS)
        show_figure(fig, "Purchase timeline by molecule")
    with right.container(border=True):
        fig = px.line(
            history, x="attempt_datetime", y="anomaly_score", markers=True,
            color_discrete_sequence=[RISK],
            labels={"attempt_datetime": "Date", "anomaly_score": "Anomaly score"},
        )
        fig.update_traces(
            name="Anomaly score",
            marker={"size": 8},
            hovertemplate="Date: %{x|%b %d, %Y}<br>Anomaly score: %{y:.1f}<extra></extra>",
        )
        fig.update_xaxes(tickformatstops=DATE_TICKS)
        fig.add_hline(
            y=98, line_dash="dash", line_color=RISK,
            annotation_text="High-risk band", annotation_position="top left",
            annotation_font_color=RISK, annotation_font_size=12,
        )
        fig.add_hline(
            y=93, line_dash="dot", line_color=WARN,
            annotation_text="Medium-risk band", annotation_position="bottom left",
            annotation_font_color=WARN, annotation_font_size=12,
        )
        show_figure(fig, "Behavioural anomaly score")
    display = history[[
        "attempt_datetime", "product_name", "molecule_name", "location_name", "normalized_units",
        "threshold_utilization", "risk_band", "reason_1",
    ]].sort_values("attempt_datetime", ascending=False)
    display.columns = ["Date", "Product", "Molecule", "Location", "Units", "Threshold utilization", "Risk", "Reason"]
    st.dataframe(display, hide_index=True, width="stretch")


def render_group_analysis(data: dict) -> None:
    page_header("Group analysis", "Connected customers through shared collectors, reused authorizations and investigation cases")
    cases = data["cases"]
    case_ids = sorted(cases["case_id"].dropna().unique())
    selected = st.selectbox("Select an investigation case", case_ids)
    group = cases[cases["case_id"] == selected].copy()
    members = sorted(group["recipient_customer_id"].dropna().unique())
    case_row = group.iloc[0]
    cols = st.columns(5)
    cols[0].metric("Customers", f"{len(members)}")
    cols[1].metric("Transactions", f"{len(group):,}")
    cols[2].metric("Locations", f"{group['location_id'].nunique()}")
    cols[3].metric("Molecules", f"{group['molecule_id'].nunique()}")
    cols[4].metric("Outcome", str(case_row["outcome"]).title())
    left, right = st.columns([1.35, 1])
    with left.container(border=True):
        fig = _case_network(group, selected)
        show_figure(fig, "Customer relationship network", 480)
    with right.container(border=True):
        st.subheader("Investigation summary")
        st.markdown(f"**Category:** {str(case_row['case_category']).replace('_', ' ').title()}")
        st.markdown(f"**Status:** {str(case_row['case_status']).title()}")
        st.markdown(f"**Shared collectors:** {group['collector_customer_id'].nunique()}")
        st.markdown(f"**Authorizations:** {group['authorization_id'].nunique()}")
        st.markdown(f"**Historical product loss:** {money(group['direct_product_loss'].sum())}")
        st.markdown(f"**Exposure prevented:** {money(group['exposure_prevented'].sum())}")
        st.caption("Connections prioritize investigation and do not prove collusion or fraud.")
    display = group[[
        "recipient_customer_id", "collector_customer_id", "authorization_id", "attempt_datetime",
        "location_name", "molecule_name", "reason_1", "priority_score",
    ]].sort_values("priority_score", ascending=False).head(100)
    display.columns = ["Customer", "Collector", "Authorization", "Date", "Location", "Molecule", "Reason", "Priority"]
    st.dataframe(display, hide_index=True, width="stretch")


def _case_network(group: pd.DataFrame, case_id: str) -> go.Figure:
    members = sorted(group["recipient_customer_id"].dropna().unique())[:20]
    collectors = sorted(group["collector_customer_id"].dropna().unique())[:4]
    nodes = [(case_id, "Case", 0.0, 0.0)]
    count = max(len(members), 1)
    for idx, customer in enumerate(members):
        angle = 2 * math.pi * idx / count
        nodes.append((customer, "Customer", 1.0 * math.cos(angle), 1.0 * math.sin(angle)))
    for idx, collector in enumerate(collectors):
        angle = 2 * math.pi * idx / max(len(collectors), 1) + .4
        nodes.append((collector, "Collector", .45 * math.cos(angle), .45 * math.sin(angle)))
    node_map = {node[0]: (node[2], node[3]) for node in nodes}
    fig = go.Figure()
    for customer in members:
        x0, y0 = node_map[case_id]
        x1, y1 = node_map[customer]
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", line={"color": "#6d8498", "width": 1}, hoverinfo="skip", showlegend=False))
    colors = {"Case": RISK, "Customer": BRAND, "Collector": WARN}
    for role in ["Case", "Customer", "Collector"]:
        role_nodes = [node for node in nodes if node[1] == role]
        if not role_nodes:
            continue
        fig.add_trace(go.Scatter(
            x=[n[2] for n in role_nodes], y=[n[3] for n in role_nodes], mode="markers+text",
            text=[n[0] if role == "Case" else n[0][-4:] for n in role_nodes],
            textposition="top center", textfont={"size": 11},
            name=role, marker={"size": 18 if role == "Case" else 12, "color": colors[role]},
            hovertext=[n[0] for n in role_nodes], hovertemplate="%{hovertext}<extra></extra>",
        ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    return fig


def render_product_trends(data: dict) -> None:
    page_header("Molecule & brand trends", "Identify products increasingly represented in alerts and investigation activity")
    monthly = data["molecule_monthly"].copy()
    monthly["month"] = pd.to_datetime(monthly["month"])
    options = sorted(monthly["molecule_name"].unique())
    selected = st.multiselect("Molecules", options, default=options[:4])
    filtered = monthly[monthly["molecule_name"].isin(selected)]
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        fig = px.line(
            filtered, x="month", y="alerts", color="molecule_name", markers=True,
            labels={"month": "Month", "alerts": "Alerts", "molecule_name": "Molecule"},
        )
        fig.update_traces(marker={"size": 7})
        show_figure(fig, "Threshold exceedances over time")
    with right.container(border=True):
        latest = filtered.groupby("molecule_name", as_index=False).agg(
            transactions=("transactions", "sum"), alerts=("alerts", "sum"), high_risk=("high_risk", "sum")
        )
        latest["alert_rate"] = latest["alerts"] / latest["transactions"]
        fig = px.scatter(
            latest, x="transactions", y="alert_rate", size="high_risk", size_max=28,
            color="molecule_name", custom_data=["alerts", "high_risk"],
            labels={
                "transactions": "Transactions",
                "alert_rate": "Alert rate",
                "molecule_name": "Molecule",
                "high_risk": "High-risk count",
            },
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Transactions: %{x:,}<br>"
                "Alert rate: %{y:.1%}<br>"
                "Alerts: %{customdata[0]:,}<br>"
                "High-risk count: %{customdata[1]:,}"
                "<extra></extra>"
            )
        )
        fig.update_yaxes(tickformat=".1%")
        show_figure(fig, "Volume versus alert rate")
    tx = data["transactions"]
    brand = tx.groupby(["brand_name", "molecule_name"], as_index=False).agg(
        transactions=("transaction_id", "count"),
        alerts=("threshold_exceeded", "sum"),
        high_risk=("risk_band", lambda values: (values == "high").sum()),
        exposure_prevented=("exposure_prevented", "sum"),
    )
    brand["alert_rate"] = brand["alerts"] / brand["transactions"]
    brand = brand.sort_values(["alert_rate", "alerts"], ascending=False)
    st.subheader("Brand monitoring")
    st.dataframe(brand.head(20), hide_index=True, width="stretch")


def render_financial(data: dict) -> None:
    page_header("Financial impact", "Separate historical losses from exposure prevented before dispensing")
    summary = data["summary"]
    cols = st.columns(4)
    cols[0].metric("Direct product loss", money(summary["historical_direct_product_loss"]))
    cols[1].metric("Foregone profit", money(summary["historical_foregone_profit"]))
    cols[2].metric("Historical unpaid exposure", money(summary["historical_unpaid_exposure"]))
    cols[3].metric("Exposure prevented", money(summary["exposure_prevented"]))
    monthly = data["monthly"].copy()
    monthly["month"] = pd.to_datetime(monthly["month"])
    monthly_long = monthly.melt(
        id_vars="month", value_vars=["direct_product_loss", "foregone_profit", "exposure_prevented"],
        var_name="measure", value_name="value",
    )
    labels = {
        "direct_product_loss": "Direct product loss",
        "foregone_profit": "Foregone profit",
        "exposure_prevented": "Exposure prevented",
    }
    monthly_long["measure"] = monthly_long["measure"].map(labels)
    left, right = st.columns([1.45, 1])
    with left.container(border=True):
        fig = px.bar(
            monthly_long, x="month", y="value", color="measure", barmode="stack",
            color_discrete_map={"Direct product loss": RISK, "Foregone profit": WARN, "Exposure prevented": GOOD},
            labels={"month": "Month", "value": "Amount", "measure": "Measure"},
        )
        fig.update_yaxes(tickprefix="$", tickformat=",")
        show_figure(fig, "Financial transition over 24 months")
    with right.container(border=True):
        claims = data["transactions"].dropna(subset=["settlement_days"]).copy()
        bucket_labels = ["30–39", "40–49", "50–59", "60–69", "70–79", "80–90"]
        claims["delay_bucket"] = pd.cut(
            claims["settlement_days"], bins=[30, 40, 50, 60, 70, 80, 91], right=False, labels=bucket_labels,
        )
        delay = (
            claims["delay_bucket"].value_counts().reindex(bucket_labels).rename_axis("delay").reset_index(name="claims")
        )
        fig = px.bar(
            delay, x="delay", y="claims", color_discrete_sequence=[BRAND],
            labels={"delay": "Days to settlement", "claims": "Claims"},
        )
        fig.update_traces(
            marker_line_width=0,
            hovertemplate="%{x} days<br>%{y:,} claims<extra></extra>",
        )
        fig.update_layout(bargap=0.34)
        fig.update_yaxes(rangemode="tozero")
        show_figure(fig, "Insurance settlement delay")
    insurer = data["insurer_summary"].copy()
    insurer["alert_rate"] = insurer["threshold_exceedances"] / insurer["transactions"]
    fig = px.bar(
        insurer, x="insurer_id", y="exposure_prevented", color="alert_rate",
        color_continuous_scale=[[0, "#1c3d4c"], [1, BRAND]],
        labels={"insurer_id": "Insurer", "exposure_prevented": "Exposure prevented", "alert_rate": "Alert rate"},
        custom_data=["transactions", "threshold_exceedances", "alert_rate"],
    )
    fig.update_traces(
        hovertemplate=(
            "Insurer: %{x}<br>"
            "Exposure prevented: $%{y:,.0f}<br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Threshold alerts: %{customdata[1]:,.0f}<br>"
            "Alert rate: %{customdata[2]:.1%}"
            "<extra></extra>"
        )
    )
    fig.update_yaxes(tickprefix="$", tickformat=",")
    fig.update_coloraxes(colorbar={"title": "Alert rate", "tickformat": ".0%"})
    show_figure(fig, "Exposure prevented by insurer (contextual comparison)")
