"""Visual system for the decision-focused Streamlit dashboard."""

APP_CSS = """
<style>
    :root {
        --ink: #e6eef6;
        --muted: #93a8bb;
        --line: #2c3d50;
        --panel: #16202c;
        --canvas: #0e1620;
        --brand: #4eb8cc;
        --brand-soft: #163544;
        --good: #3dcea0;
        --warn: #e3b15a;
        --risk: #ef7a6a;
    }
    [data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] .stRadio label { padding: .35rem .25rem; }
    .block-container { max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -.02em; }
    h1 { font-size: 2rem !important; font-weight: 650 !important; margin-bottom: .1rem !important; }
    h2 { font-size: 1.25rem !important; font-weight: 650 !important; }
    h3 { font-size: 1rem !important; font-weight: 650 !important; }
    .page-subtitle { color: var(--muted); margin-bottom: 1.25rem; }
    .synthetic-note { padding: .75rem 1rem; border-left: 3px solid var(--brand); background: var(--brand-soft); color: #d5e6ee; border-radius: 0 .5rem .5rem 0; margin-bottom: 1rem; }
    [data-testid="stHorizontalBlock"] { align-items: stretch !important; }
    [data-testid="stColumn"] { display: flex; flex-direction: column; }
    [data-testid="stColumn"] > [data-testid="stVerticalBlock"] { flex: 1 1 auto; height: 100%; }
    [data-testid="stElementContainer"]:has(> [data-testid="stMetric"]) { flex: 1 1 auto; display: flex; flex-direction: column; }
    [data-testid="stMetric"] { background: var(--panel); border: 1px solid var(--line); border-radius: .75rem; padding: .85rem 1rem; height: 100%; box-sizing: border-box; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); }
    [data-testid="stVerticalBlockBorderWrapper"] { background: var(--panel); border-color: var(--line) !important; border-radius: .8rem; }
    .decision-box { background: var(--panel); border: 1px solid var(--line); border-radius: .75rem; padding: 1rem; margin-bottom: .75rem; color: var(--ink); }
    .decision-box strong { color: var(--ink); }
    .reason-pill { display: inline-block; padding: .3rem .55rem; margin: .15rem .2rem .15rem 0; border-radius: 999px; background: var(--brand-soft); color: #b7e4ef; font-size: .82rem; }
    .risk-high { color: var(--risk); font-weight: 650; }
    .risk-medium { color: var(--warn); font-weight: 650; }
    .risk-low { color: var(--good); font-weight: 650; }
    .stDataFrame { border: 1px solid var(--line); border-radius: .65rem; overflow: hidden; }
    footer { visibility: hidden; }
</style>
"""

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, Arial, sans-serif", "color": "#c5d4e0", "size": 12},
    "margin": {"l": 64, "r": 24, "t": 84, "b": 56},
    "legend": {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "x": 0,
        "xanchor": "left",
        "font": {"color": "#c5d4e0"},
        "title": {"text": ""},
    },
    "hoverlabel": {"bgcolor": "#101820", "font_color": "#e6eef6", "bordercolor": "#2c3d50"},
}

