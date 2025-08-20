import streamlit as st
import pandas as pd
import plotly.express as px

from processing.pipeline import (
    read_workbook,
    detect_template_type,
    validate_df,
    transform_results,
    transform_equity_results,
)
from processing.reporting import generate_excel_report
from processing.pdf_report import generate_pdf_report
from processing.schema import *
from plot import format_pie

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(
    page_title="Portfolio Health Check",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Portfolio Health Check")

# -----------------------------
# File Upload
# -----------------------------
upload = st.file_uploader("Upload Portfolio Workbook (.xlsx)", type=["xlsx"])
if upload:
    try:
        xls, df = read_workbook(upload)
        template_type = detect_template_type(xls)

        st.success(f"Detected template: {template_type}")

        # -----------------------------
        # Portfolio Master Dashboard
        # -----------------------------
        if template_type == "PortfolioMaster":
            res = transform_results(df, xls)
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                "Summary", "By Asset Class", "By Sub-Asset",
                "Policy vs Actual", "Geography", "FX", "Liquidity & ESG"
            ])

            with tab1:
                st.subheader("Portfolio Summary")
                st.dataframe(res["summary"])

            with tab2:
                st.subheader("By Asset Class")
                fig = px.pie(res["asset_class"], names="Asset Class", values="USD Total")
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                st.subheader("By Sub-Asset Class")
                fig = px.pie(res["sub_asset"], names="Sub Asset Class", values="USD Total")
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                st.subheader("Policy vs Actual")
                fig = px.bar(res["policy_vs_actual"].melt(
                    id_vars="Asset Class",
                    value_vars=["Portfolio %", "Policy %"]),
                    x="Asset Class", y="value", color="variable", barmode="group"
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab5:
                st.subheader("Geography")
                st.plotly_chart(res["choropleth"], use_container_width=True)

            with tab6:
                st.subheader("FX Exposure")
                fig = px.bar(res["fx"], x="Currency", y="USD Total")
                st.plotly_chart(fig, use_container_width=True)

            with tab7:
                st.subheader("Liquidity, Fees & ESG")
                st.plotly_chart(res["liquidity"], use_container_width=True)
                st.plotly_chart(res["fees"], use_container_width=True)
                st.plotly_chart(res["esg"], use_container_width=True)

        # -----------------------------
        # Equity Dashboard
        # -----------------------------
        if template_type == "EquityAssetList":
            policy_df = None
            if "Policy" in xls.sheet_names:
                policy_df = pd.read_excel(upload, sheet_name="Policy")

            res = transform_equity_results(df, policy_df)

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Sector vs Benchmark", "Market Cap", "Style", "Revenue", "Valuation", "Factors"
            ])

            with tab1:
                st.subheader("Sector Allocation vs Benchmark")
                fig0 = px.bar(
                    res["sector_vs_benchmark"].melt(
                        id_vars="Sector",
                        value_vars=["Portfolio Weight %", "Policy Weight %"]
                    ),
                    x="Sector", y="value", color="variable", barmode="group"
                )
                st.plotly_chart(fig0, use_container_width=True)

            with tab2:
                st.subheader("Market Cap Distribution")
                fig1 = px.bar(res["market_cap"], x="Market Cap Bucket", y="Weight %")
                st.plotly_chart(fig1, use_container_width=True)

            with tab3:
                st.subheader("Style Box Exposures")
                fig2 = px.bar(res["style_box"], x="Style", y="Exposure")
                st.plotly_chart(fig2, use_container_width=True)

            with tab4:
                st.subheader("Revenue Exposure Heatmap")
                fig3 = px.treemap(res["revenue_exposure"],
                                  path=["Revenue Exposure Region"],
                                  values="Revenue Exposure %")
                st.plotly_chart(fig3, use_container_width=True)

            with tab5:
                st.subheader("Valuation Scatter (PE vs EPS Growth)")
                fig4 = px.scatter(
                    res["valuation_scatter"],
                    x="PE", y="EPS Growth fwd12m %",
                    size="Weight %", hover_name="Security"
                )
                st.plotly_chart(fig4, use_container_width=True)

            with tab6:
                st.subheader("Factor Exposure Spider")
                fig5 = px.line_polar(
                    res["factor_spider"], r="Exposure", theta="Style", line_close=True
                )
                st.plotly_chart(fig5, use_container_width=True)

        # -----------------------------
        # Fixed Income Dashboard
        # -----------------------------
        if template_type == "FixedIncomeAssetList":
            st.subheader("Fixed Income dashboard coming soon...")

        # -----------------------------
        # Export Buttons
        # -----------------------------
        st.sidebar.subheader("Exports")
        excel_bytes = generate_excel_report(df)
        st.sidebar.download_button(
            "Download Excel Report", data=excel_bytes,
            file_name="portfolio_health.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        pdf_bytes = generate_pdf_report(df)
        st.sidebar.download_button(
            "Download PDF Report", data=pdf_bytes,
            file_name="portfolio_health.pdf", mime="application/pdf"
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")
