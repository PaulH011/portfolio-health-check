import streamlit as st

# FIRST Streamlit call — only once
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

# (Optional) simple password — remove this block if you don't want it
if "APP_PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("App password", type="password")
    if pwd != st.secrets["APP_PASSWORD"]:
        st.stop()

st.title("Portfolio Health Check")

with st.sidebar:
    st.header("Upload")
    file = st.file_uploader("Upload standardized Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)

if not file:
    st.info("Upload a standardized template to begin.")
    st.stop()

# --- Read workbook & detect type
try:
    sheets, meta_str = read_workbook(file)
except Exception as e:
    st.error(f"Template read failed: {e}")
    st.stop()

detected_type = detect_template_type(sheets, meta_str)
tmpl_type = st.sidebar.selectbox(
    "Template type",
    options=["PortfolioMaster", "EquityAssetList", "FixedIncomeAssetList"],
    index=["PortfolioMaster", "EquityAssetList", "FixedIncomeAssetList"].index(detected_type)
)

sheet_name = get_required_sheet_for_type(tmpl_type)
df = sheets.get(sheet_name) or next((sheets[k] for k in sheets if k.lower() == sheet_name.lower()), None)
if df is None or df.empty:
    st.error(f"Missing or empty sheet: '{sheet_name}'.")
    st.stop()

# --- Validate
errors = validate_df(df, tmpl_type)
c1, c2 = st.columns([2,1])
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

# --- Transform & Dashboards
results = transform_results(df, tmpl_type)
st.caption(f"Detected: **{detected_type}**  •  Validating/processing as: **{tmpl_type}**  •  Source sheet: **{sheet_name}**")

if tmpl_type == "PortfolioMaster":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Asset Class", "By Sub-Asset", "Currency / Liquidity"])
    with tab1:
        m = results["metrics"]
        st.metric("Rows", m["n_rows"])
        st.metric("Total USD", f'{m["usd_total_sum"]:,.2f}')
        st.dataframe(results["top_assets"])
    with tab2:
        dfv = results["by_asset_class"]
        fig = px.bar(dfv, x="Asset Class", y="USD Total", text="USD Total")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab3:
        dfv = results["by_sub_asset"]
        fig = px.bar(dfv, x="Sub Asset Class", y="USD Total", text="USD Total")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab4:
        lc = results["by_liquidity"]; fx = results["by_fx"]
        st.markdown("**Liquidity**"); st.dataframe(lc)
        st.markdown("**Currency**"); st.dataframe(fx)

elif tmpl_type == "EquityAssetList":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Sector", "By Region", "Top Positions"])
    with tab1:
        m = results["metrics"]
        st.metric("Positions", m["n_rows"])
        st.metric("Market Value (USD)", f'{m["mv_sum"]:,.2f}')
        st.metric("Weight % (sum)", f'{m["w_sum"]:.2f}')
    with tab2:
        dfv = results["by_sector"]
        fig = px.bar(dfv, x="Sector (GICS)", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab3:
        dfv = results["by_region"]
        fig = px.bar(dfv, x="Region", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab4:
        st.dataframe(results["top_positions"])

elif tmpl_type == "FixedIncomeAssetList":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Rating", "Maturity Ladder", "Duration Buckets"])
    with tab1:
        m = results["metrics"]
        st.metric("Bonds", m["n_rows"])
        st.metric("Market Value (USD)", f'{m["mv_sum"]:,.2f}')
        st.metric("Weight % (sum)", f'{m["w_sum"]:.2f}')
        st.metric("Mod. Duration (mv-weighted)", f'{m["dur_wt_avg"]:.2f}')
    with tab2:
        dfv = results["by_rating"]
        fig = px.bar(dfv, x="Rating", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab3:
        dfv = results["maturity_buckets"]
        fig = px.bar(dfv, x="Bucket", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)
    with tab4:
        dfv = results["duration_buckets"]
        fig = px.bar(dfv, x="Bucket", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(dfv)

# --- Artifacts
xlsx_bytes = build_report_xlsx(results)
st.download_button("Download report.xlsx", xlsx_bytes, file_name="portfolio_health_report.xlsx")
