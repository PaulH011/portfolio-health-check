import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


def _table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    return t


def _summary_blocks(df: pd.DataFrame) -> list:
    blocks = []
    if "Weight %" in df.columns:
        total_w = float(pd.to_numeric(df["Weight %"], errors="coerce").fillna(0).sum())
        blocks.append(["Total Weight %", f"{total_w:,.2f}"])
    if "USD Total" in df.columns:
        total_usd = float(pd.to_numeric(df["USD Total"], errors="coerce").fillna(0).sum())
        blocks.append(["Total USD", f"{total_usd:,.0f}"])
    if not blocks:
        blocks = [["Rows", f"{len(df):,}"], ["Columns", f"{len(df.columns):,}"]]
    return [["Metric", "Value"], *blocks]


def _sector_alloc(df: pd.DataFrame) -> list | None:
    if {"Sector", "Weight %"}.issubset(df.columns):
        tmp = (
            df[["Sector", "Weight %"]]
            .assign(**{"Weight %": pd.to_numeric(df["Weight %"], errors="coerce").fillna(0)})
            .groupby("Sector", dropna=False)["Weight %"]
            .sum()
            .reset_index()
            .sort_values("Weight %", ascending=False)
        )
        data = [["Sector", "Weight %"], *tmp.values.tolist()]
        return data
    return None


def _asset_alloc(df: pd.DataFrame) -> list | None:
    if {"Asset Class", "USD Total"}.issubset(df.columns):
        tmp = (
            df[["Asset Class", "USD Total"]]
            .assign(**{"USD Total": pd.to_numeric(df["USD Total"], errors="coerce").fillna(0)})
            .groupby("Asset Class", dropna=False)["USD Total"]
            .sum()
            .reset_index()
            .sort_values("USD Total", ascending=False)
        )
        data = [["Asset Class", "USD Total"], *tmp.values.tolist()]
        return data
    return None


def generate_pdf_report(
    df: pd.DataFrame,
    title: str = "Portfolio Health Check",
    logo_path: str = "assets/parkview_logo.png",
) -> bytes:
    """
    Build a white-themed PDF (centered logo, clean tables) and return bytes.
    Safe against missing columns; shows whatever is available.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = []

    # Header: centered logo (if available) + title
    try:
        img = Image(logo_path, width=40 * mm, height=40 * mm)
        img.hAlign = "CENTER"
        story += [img, Spacer(1, 6 * mm)]
    except Exception:
        # no logo; continue
        pass

    story += [
        Paragraph(title, h1),
        Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), body),
        Spacer(1, 8 * mm),
    ]

    # Summary block
    story += [Paragraph("Summary", h2)]
    story += [_table(_summary_blocks(df), col_widths=[60 * mm, 60 * mm]), Spacer(1, 6 * mm)]

    # Optional: Sector Allocation table
    sector_data = _sector_alloc(df)
    if sector_data:
        story += [Paragraph("Sector Allocation", h2)]
        story += [_table(sector_data, col_widths=[80 * mm, 40 * mm]), Spacer(1, 6 * mm)]

    # Optional: Asset Class Allocation table
    asset_data = _asset_alloc(df)
    if asset_data:
        story += [Paragraph("Asset Class Allocation", h2)]
        story += [_table(asset_data, col_widths=[80 * mm, 40 * mm]), Spacer(1, 6 * mm)]

    # Build document
    doc.build(story)
    return buf.getvalue()
