# app.py
import streamlit as st

# ---- Must be first Streamlit call ----
st.set_page_config(page_title="Portfolio Health Check", layout="wide")

import pandas as pd
import plotly.express as px

from processing.pipeline import (
    read_workbook,
    detect_template_type,
    get_required_sheet_for_type,
    validate_df,
    transform_results,
)
from processing.reporting import build_report_xlsx, build_validation_report
from processing.pdf_report import build_pdf_report
from plot import (
    pie_asset_class, pie_sub_asset,
    pie_equity_sector, pie_equity_region, pie_fi_rating
)

# ------------ Optional password gate ------------
if "APP_PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("App password", type="password")
    if pwd != st.secrets["APP_PASSWORD"]:
        st.stop()

st.title("Portfolio Health Check")

# ------------ Sidebar: upload ------------
with st.sidebar:
    st.header("Upload")
    file = st.file_uploader(
        "Upload standardized Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False
    )

if not file:
    st.info("Upload a standardized template to begin.")
    st.stop()

# ------------ Read workbook & detect type ------------
try:
    sheets, meta_str = read_workbook(file)  # dict[str, DataFrame], "Template v1.0 - XYZ" or None
except Exception as e:
    st.error(f"Template read failed: {e}")
    st.stop()

detected_type = detect_template_type(sheets, meta_str)
tmpl_options = ["PortfolioMaster", "EquityAssetList", "FixedIncomeAssetList"]
with st.sidebar:
    tmpl_type = st.selectbox(
        "Template type", options=tmpl_options, index=tmpl_options.index(detected_type)
    )

# ------------ Safe sheet fetch (no boolean eval on DataFrames) ------------
sheet_name = get_required_sheet_for_type(tmpl_type)

# Exact match
df = sheets.get(sheet_name)

# Case-insensitive fallback + allow 'Pastor' alias for PortfolioMaster
if df is None:
    for k, v in sheets.items():
        kl = k.lower()
        if kl == sheet_name.lower():
            df = v
            break
        if tmpl_type == "PortfolioMaster" and kl == "pastor":
            df = v
            break

if df is None:
    st.error(f"Missing required sheet: '{sheet_name}'.")
    st.stop()

if df.shape[0] == 0:
    st.warning(
        f"Sheet '{sheet_name}' is present but has 0 rows. "
        "Download a sample template, fill it, and re-upload."
    )
    st.stop()

# ------------ Validation ------------
errors = validate_df(df, tmpl_type)
c1, c2 = st.columns([2, 1])
with c1:
    st.subheader("Validation")
    if errors:
        st.error(f"{len(errors)} validation issue(s) found")
        st.dataframe(pd.DataFrame(errors))
    else:
        st.success("Validation passed")
with c2:
    vb = build_validation_report(errors)
    st.download_button("Download Validation Report", vb, file_name="validation_report.xlsx")

if errors:
    st.stop()

# ------------ Transform ------------
results = transform_results(df, tmpl_type)
st.caption(
    f"Detected: **{detected_type}**  •  Processing as: **{tmpl_type}**  •  Source sheet: **{sheet_name}**"
)

# Collect figures for PDF
figs = {}

# ------------ Dashboards per template ------------
if tmpl_type == "PortfolioMaster":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Asset Class", "By Sub-Asset", "Currency / Liquidity"])

    with tab1:
        m = results["metrics"]
        cA, cB = st.columns(2)
        cA.metric("Rows", m["n_rows"])
        cB.metric("Total USD", f'{m["usd_total_sum"]:,.2f}')
        st.markdown("**Top assets**")
        st.dataframe(results["top_assets"])

    # Donut: Asset Class
    with tab2:
        dfv = results["by_asset_class"].copy()
        total = dfv["USD Total"].sum()
        dfv["% of Total"] = (dfv["USD Total"] / total) * 100 if total else 0.0

        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="pm_assetclass_labels"
        )
        mode = {"Value ($)": "value", "% of total": "%", "Both": "both"}[label_mode]

        fig, table = pie_asset_class(results, label_mode=mode)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv[["Asset Class", "USD Total", "% of Total"]])
        figs["pm_asset_pie"] = fig

    # Donut: Sub-Asset
    with tab3:
        dfv = results["by_sub_asset"].copy()
        total = dfv["USD Total"].sum()
        dfv["% of Total"] = (dfv["USD Total"] / total) * 100 if total else 0.0

        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="pm_subasset_labels"
        )
        mode = {"Value ($)": "value", "% of total": "%", "Both": "both"}[label_mode]

        fig, table = pie_sub_asset(results, label_mode=mode)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv[["Sub Asset Class", "USD Total", "% of Total"]])
        figs["pm_subasset_pie"] = fig

    # Bars: Currency & Liquidity
    with tab4:
        fx = results["by_fx"]
        liq = results["by_liquidity"]

        st.markdown("**Currency**")
        fig_fx = px.bar(fx, x="FX", y="USD Total", text="USD Total")
        st.plotly_chart(fig_fx, use_container_width=True)
        st.dataframe(fx)

        st.markdown("**Liquidity**")
        fig_lq = px.bar(liq, x="Liquid/Illiquid", y="USD Total", text="USD Total")
        st.plotly_chart(fig_lq, use_container_width=True)
        st.dataframe(liq)

        figs["pm_currency_bar"] = fig_fx
        figs["pm_liquidity_bar"] = fig_lq

elif tmpl_type == "EquityAssetList":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Sector", "By Region", "Top Positions"])

    with tab1:
        m = results["metrics"]
        cA, cB, cC = st.columns(3)
        cA.metric("Positions", m["n_rows"])
        cB.metric("Market Value (USD)", f'{m["mv_sum"]:,.2f}')
        cC.metric("Weight % (sum)", f'{m["w_sum"]:.2f}')

    with tab2:
        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="eq_sector_labels"
        )
        mode = {"Value ($)": "value", "% of total": "%", "Both": "both"}[label_mode]
        fig, table = pie_equity_sector(results, label_mode=mode)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(table.rename(columns={"Weight": "Weight %"}))
        figs["eq_sector_pie"] = fig

    with tab3:
        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="eq_region_labels"
        )
        mode = {"Value ($)": "value", "% of total": "%", "Both": "both"}[label_mode]
        fig, table = pie_equity_region(results, label_mode=mode)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(table.rename(columns={"Weight": "Weight %"}))
        figs["eq_region_pie"] = fig

    with tab4:
        top = results["top_positions"].copy()
        fig_top = px.bar(top.head(15), x="Asset (Security Name)", y="Market Value (USD)", text="Market Value (USD)")
        fig_top.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_top, use_container_width=True)
        st.dataframe(top)
        figs["eq_top_bar"] = fig_top

elif tmpl_type == "FixedIncomeAssetList":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Rating", "Maturity Ladder", "Duration Buckets"])

    with tab1:
        m = results["metrics"]
        cA, cB, cC, cD = st.columns(4)
        cA.metric("Bonds", m["n_rows"])
        cB.metric("Market Value (USD)", f'{m["mv_sum"]:,.2f}')
        cC.metric("Weight % (sum)", f'{m["w_sum"]:.2f}')
        cD.metric("Mod. Duration (mv-weighted)", f'{m["dur_wt_avg"]:.2f}')

    with tab2:
        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="fi_rating_labels"
        )
        mode = {"Value ($)": "value", "% of total": "%", "Both": "both"}[label_mode]
        fig, table = pie_fi_rating(results, label_mode=mode)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(table.rename(columns={"Weight": "Weight %"}))
        figs["fi_rating_pie"] = fig

    with tab3:
        mat = results["maturity_buckets"]
        fig_mat = px.bar(mat, x="Bucket", y="Weight %", text="Weight %", title="Maturity Ladder")
        st.plotly_chart(fig_mat, use_container_width=True)
        st.dataframe(mat)
        figs["fi_maturity_bar"] = fig_mat

    with tab4:
        dur = results["duration_buckets"]
        fig_dur = px.bar(dur, x="Bucket", y="Weight %", text="Weight %", title="Duration Buckets")
        st.plotly_chart(fig_dur, use_container_width=True)
        st.dataframe(dur)
        figs["fi_duration_bar"] = fig_dur

# ------------ Exports ------------
xlsx_bytes = build_report_xlsx(results)
st.download_button("Download report.xlsx", xlsx_bytes, file_name="portfolio_health_report.xlsx")

pdf_bytes = build_pdf_report(
    tmpl_type, results, figs, logo_path="assets/parkview_logo.png"
)
st.download_button(
    "Download PDF report", pdf_bytes,
    file_name="portfolio_health_report.pdf", mime="application/pdf"
)
