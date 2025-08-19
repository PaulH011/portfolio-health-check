import streamlit as st

# ---- MUST be the first Streamlit call (and only once) ----
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


# ---- (Optional) simple password. Delete this block to disable. ----
if "APP_PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("App password", type="password")
    if pwd != st.secrets["APP_PASSWORD"]:
        st.stop()


st.title("Portfolio Health Check")

# ---------------- Sidebar: upload + template switcher ----------------
with st.sidebar:
    st.header("Upload")
    file = st.file_uploader("Upload standardized Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)

if not file:
    st.info("Upload a standardized template to begin.")
    st.stop()

# ---------------- Read workbook & detect template type ----------------
try:
    sheets, meta_str = read_workbook(file)  # dict[str, DataFrame], "Template v1.0 - XYZ" or None
except Exception as e:
    st.error(f"Template read failed: {e}")
    st.stop()

detected_type = detect_template_type(sheets, meta_str)
tmpl_options = ["PortfolioMaster", "EquityAssetList", "FixedIncomeAssetList"]
with st.sidebar:
    tmpl_type = st.selectbox("Template type", options=tmpl_options, index=tmpl_options.index(detected_type))

# ---------------- Safe sheet fetch (no boolean-eval on DataFrames) ----------------
sheet_name = get_required_sheet_for_type(tmpl_type)

# 1) exact match
df = sheets.get(sheet_name)

# 2) case-insensitive + allow 'Pastor' alias for PortfolioMaster
if df is None:
    for k, v in sheets.items():
        kl = k.lower()
        if kl == sheet_name.lower():
            df = v
            break
        if tmpl_type == "PortfolioMaster" and kl == "pastor":
            df = v
            break

# hard-missing sheet -> stop
if df is None:
    st.error(f"Missing required sheet: '{sheet_name}'.")
    st.stop()

# allow empty sheet (blank template) but stop gracefully
if df.shape[0] == 0:
    st.warning(f"Sheet '{sheet_name}' is present but has 0 rows. "
               "Download the sample template, add rows, and re-upload.")
    st.stop()


# ---------------- Validation ----------------
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

# ---------------- Transform & Dashboards ----------------
results = transform_results(df, tmpl_type)
st.caption(
    f"Detected: **{detected_type}**  •  Processing as: **{tmpl_type}**  •  Source sheet: **{sheet_name}**"
)

if tmpl_type == "PortfolioMaster":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Asset Class", "By Sub-Asset", "Currency / Liquidity"])

    with tab1:
        m = results["metrics"]
        cA, cB = st.columns(2)
        cA.metric("Rows", m["n_rows"])
        cB.metric("Total USD", f'{m["usd_total_sum"]:,.2f}')
        st.markdown("**Top assets**")
        st.dataframe(results["top_assets"])

    with tab2:
        dfv = results["by_asset_class"].copy()
        total = dfv["USD Total"].sum()
        dfv["% of Total"] = (dfv["USD Total"] / total) * 100
    
        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="pm_assetclass_labels"
        )
    
        fig = px.pie(
            dfv,
            names="Asset Class",
            values="USD Total",
            hole=0.25,
            title="By Asset Class"
        )
        if label_mode == "Value ($)":
            fig.update_traces(textinfo="label+value")
        elif label_mode == "% of total":
            fig.update_traces(textinfo="label+percent")
        else:
            fig.update_traces(textinfo="label+value+percent")
        fig.update_traces(textposition="inside")
        st.plotly_chart(fig, use_container_width=True)
    
        st.dataframe(dfv[["Asset Class", "USD Total", "% of Total"]])

    with tab3:
        dfv = results["by_sub_asset"].copy()
        total = dfv["USD Total"].sum()
        dfv["% of Total"] = (dfv["USD Total"] / total) * 100
    
        label_mode = st.radio(
            "Labels", ["Value ($)", "% of total", "Both"],
            index=2, horizontal=True, key="pm_subasset_labels"
        )
    
        fig = px.pie(
            dfv,
            names="Sub Asset Class",
            values="USD Total",
            hole=0.25,
            title="By Sub-Asset"
        )
        if label_mode == "Value ($)":
            fig.update_traces(textinfo="label+value")
        elif label_mode == "% of total":
            fig.update_traces(textinfo="label+percent")
        else:
            fig.update_traces(textinfo="label+value+percent")
        fig.update_traces(textposition="inside")
        st.plotly_chart(fig, use_container_width=True)
    
        st.dataframe(dfv[["Sub Asset Class", "USD Total", "% of Total"]])

    with tab4:
        st.markdown("**Liquidity**")
        st.dataframe(results["by_liquidity"])
        st.markdown("**Currency**")
        st.dataframe(results["by_fx"])


elif tmpl_type == "EquityAssetList":
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "By Sector", "By Region", "Top Positions"])

    with tab1:
        m = results["metrics"]
        cA, cB, cC = st.columns(3)
        cA.metric("Positions", m["n_rows"])
        cB.metric("Market Value (USD)", f'{m["mv_sum"]:,.2f}')
        cC.metric("Weight % (sum)", f'{m["w_sum"]:.2f}')

    with tab2:
        dfv = results["by_sector"]
        fig = px.bar(dfv, x="Sector (GICS)", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv)

    with tab3:
        dfv = results["by_region"]
        fig = px.bar(dfv, x="Region", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv)

    with tab4:
        st.dataframe(results["top_positions"])


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
        dfv = results["by_rating"]
        fig = px.bar(dfv, x="Rating", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv)

    with tab3:
        dfv = results["maturity_buckets"]
        fig = px.bar(dfv, x="Bucket", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv)

    with tab4:
        dfv = results["duration_buckets"]
        fig = px.bar(dfv, x="Bucket", y="Weight %", text="Weight %")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfv)

# ---------------- Report export ----------------
xlsx_bytes = build_report_xlsx(results)
st.download_button("Download report.xlsx", xlsx_bytes, file_name="portfolio_health_report.xlsx")


