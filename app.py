import streamlit as st
import pandas as pd
import plotly.express as px

from processing.pipeline import read_template, validate_positions, transform
from processing.reporting import build_report_xlsx, build_validation_report

# MUST be first Streamlit call
st.set_page_config(page_title="Portfolio Health Check", layout="wide")

# Optional auth (after set_page_config)
if "APP_PASSWORD" in st.secrets:
    with st.sidebar:
        pwd = st.text_input("App password", type="password")
    if pwd != st.secrets["APP_PASSWORD"]:
        st.stop()

from processing.pipeline import read_template, validate_positions, transform
from processing.reporting import build_report_xlsx, build_validation_report, build_pdf_from_html

st.set_page_config(page_title="Portfolio Health Check", layout="wide")

st.title("Portfolio Health Check")

with st.sidebar:
    st.header("Upload")
    file = st.file_uploader("Upload standardized Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)

if not file:
    st.info("Upload a standardized template to begin.")
    st.stop()

# Parse + validate
try:
    sheets = read_template(file)
    # Expect "Positions" sheet — adapt name if different
    pos = sheets.get("Positions")
    if pos is None:
        st.error("Missing required sheet: 'Positions'")
        st.stop()
    # normalize column names
    pos.columns = [c.strip() for c in pos.columns]
except Exception as e:
    st.error(f"Template read failed: {e}")
    st.stop()

errors = validate_positions(pos)

col_a, col_b = st.columns([2,1])
with col_a:
    st.subheader("Validation")
    if errors:
        st.error(f"{len(errors)} validation issue(s) found")
        st.dataframe(pd.DataFrame(errors))
    else:
        st.success("Validation passed")

with col_b:
    if st.button("Download Validation Report"):
        vb = build_validation_report(errors)
        st.download_button("Save validation.xlsx", vb, file_name="validation_report.xlsx")

if errors:
    st.stop()

# Transform & show dashboards
results = transform(pos)

tab1, tab2, tab3, tab4 = st.tabs(["Summary","By Asset Class","By Region","Currency"])

with tab1:
    m = results["metrics"]
    st.metric("Gross Exposure (sum weights)", f'{m["gross_exposure"]:.2f}')
    st.metric("Positions", m["n_positions"])

with tab2:
    df = results["alloc_asset"]
    fig = px.bar(df, x="AssetClass", y="Weight", text="Weight")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df)

with tab3:
    df = results["alloc_region"]
    fig = px.bar(df, x="Region", y="Weight", text="Weight")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df)

with tab4:
    df = results["currency_exp"]
    fig = px.bar(df, x="Currency", y="Weight", text="Weight")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df)

# Artifacts
st.subheader("Artifacts")
xlsx_bytes = build_report_xlsx(results)
st.download_button("Download report.xlsx", xlsx_bytes, file_name="portfolio_health_report.xlsx")

# PDF export skipped in Streamlit Cloud for faster build
st.info("PDF export is disabled in this version to speed up deployment. Use Excel report instead.")




