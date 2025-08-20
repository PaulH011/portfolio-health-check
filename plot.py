# plot.py
"""
Plot helpers for the Portfolio Health Check app.
- Centralizes pie/donut builders and formatting.
- Pie helpers return (fig, table_with_%_of_total) so you can also show a table.
"""

from typing import Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------- Formatting helpers (call after creating a fig) ----------------

def _apply_common_layout(fig: go.Figure) -> go.Figure:
    # Legend BELOW the plot, horizontal, left aligned
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=-0.18,              # below the plot area
            x=0.0,
            xanchor="left",
            yanchor="top",
            title_text=""
        ),
        # Leave headroom for title; extra bottom for legend
        margin=dict(l=8, r=8, t=50, b=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig

def format_pie(fig: go.Figure) -> go.Figure:
    fig.update_traces(
        textposition="inside",
        textfont=dict(size=12),
        hovertemplate="%{label}<br>%{percent:.1%} (%{value:,.0f})<extra></extra>",
    )
    return _apply_common_layout(fig)

def format_bar(fig: go.Figure) -> go.Figure:
    fig.update_traces(
        texttemplate="%{y:,.0f}",
        hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
    )
    fig.update_yaxes(tickformat=",.0f", gridcolor="#E9EEF4")
    fig.update_xaxes(gridcolor="#F4F7FA")
    return _apply_common_layout(fig)

def format_waterfall(fig: go.Figure) -> go.Figure:
    fig.update_yaxes(tickformat=",.0f", gridcolor="#E9EEF4")
    fig.update_xaxes(gridcolor="#F4F7FA")
    return _apply_common_layout(fig)


# ---------------- Core pie/donut builder ----------------

_LABEL_TEXTINFO = {
    "value": "label+value",
    "%": "label+percent",
    "both": "label+value+percent",
}

def _add_pct_of_total(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    out = df.copy()
    total = pd.to_numeric(out[value_col], errors="coerce").fillna(0.0).sum()
    out["% of Total"] = 0.0 if total == 0 else (out[value_col] / total * 100.0)
    return out

def pie_donut(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    *,
    label_mode: str = "both",   # "value" | "%" | "both"
    title: Optional[str] = None,
    hole: float = 0.25,
    sort_desc: bool = True,
) -> Tuple[go.Figure, pd.DataFrame]:
    """
    Generic donut pie. Returns (figure, table_with_%_of_total).
    """
    work = df[[names_col, values_col]].copy()
    work[values_col] = pd.to_numeric(work[values_col], errors="coerce").fillna(0.0)
    if sort_desc:
        work = work.sort_values(values_col, ascending=False)

    fig = px.pie(
        work,
        names=names_col,
        values=values_col,
        hole=hole,
        title=title,
    )
    # Left-align title so it doesn't sit under centered legend
    fig.update_layout(
        title=dict(y=0.98, x=0.0, xanchor="left", yanchor="top", font=dict(size=16))
    )
    fig.update_traces(textinfo=_LABEL_TEXTINFO.get(label_mode, "label+value+percent"))
    format_pie(fig)

    table = _add_pct_of_total(work, values_col)
    return fig, table


# ---------------- Convenience wrappers used by app.py ----------------

# PortfolioMaster
def pie_asset_class(results: dict, label_mode: str = "both") -> Tuple[go.Figure, pd.DataFrame]:
    df = results["by_asset_class"].rename(columns={"USD Total": "Value"})
    return pie_donut(df, "Asset Class", "Value", label_mode=label_mode, title="By Asset Class")

def pie_sub_asset(results: dict, label_mode: str = "both") -> Tuple[go.Figure, pd.DataFrame]:
    df = results["by_sub_asset"].rename(columns={"USD Total": "Value"})
    return pie_donut(df, "Sub Asset Class", "Value", label_mode=label_mode, title="By Sub-Asset")

# EquityAssetList
def pie_equity_sector(results: dict, label_mode: str = "both") -> Tuple[go.Figure, pd.DataFrame]:
    df = results["by_sector"].rename(columns={"Weight %": "Weight"})
    return pie_donut(df, "Sector (GICS)", "Weight", label_mode=label_mode, title="Equity by Sector")

def pie_equity_region(results: dict, label_mode: str = "both") -> Tuple[go.Figure, pd.DataFrame]:
    df = results["by_region"].rename(columns={"Weight %": "Weight"})
    return pie_donut(df, "Region", "Weight", label_mode=label_mode, title="Equity by Region")

# FixedIncomeAssetList
def pie_fi_rating(results: dict, label_mode: str = "both") -> Tuple[go.Figure, pd.DataFrame]:
    df = results["by_rating"].rename(columns={"Weight %": "Weight"})
    return pie_donut(df, "Rating", "Weight", label_mode=label_mode, title="Fixed Income by Rating")
