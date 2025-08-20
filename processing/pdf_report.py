# processing/pdf_report.py
from __future__ import annotations
import io
import datetime as dt
from typing import Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
import plotly.graph_objects as go

def _fig_to_png_bytes(fig: go.Figure, scale: float = 2.0) -> bytes:
    # requires kaleido
    return fig.to_image(format="png", scale=scale)

def _img_flowable(png_bytes: bytes, max_width_mm: float = 170) -> Image:
    bio = io.BytesIO(png_bytes)
    img = Image(bio)
    # Constrain width, keep aspect
    max_w = max_width_mm * mm
    w, h = img.wrap(0, 0)
    if w > max_w:
        ratio = max_w / w
        img._restrictSize(max_w, h * ratio)
    return img

def _kv_table(data: dict) -> Table:
    rows = [[k, v] for k, v in data.items()]
    t = Table(rows, colWidths=[55*mm, 110*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.Color(0.98,0.98,0.98)]),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    return t

def _header(canvas, doc, logo_path: str, title: str):
    canvas.saveState()
    if logo_path:
        try:
            canvas.drawImage(logo_path, 15*mm, doc.height + 25*mm, width=35*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColor(colors.HexColor("#1F3B63"))
    canvas.drawRightString(doc.width + 15*mm, doc.height + 35*mm, title)
    canvas.setLineWidth(0.3)
    canvas.setStrokeColor(colors.HexColor("#1F3B63"))
    canvas.line(15*mm, doc.height + 24*mm, doc.width + 15*mm, doc.height + 24*mm)
    canvas.restoreState()

def build_pdf_report(template_type: str, results: dict, figs: Dict[str, go.Figure], logo_path: str = "assets/parkview_logo.png") -> bytes:
    """
    Build a branded multi-page PDF. 'figs' is a dict of plotly figures.
    Returns PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm, topMargin=40*mm, bottomMargin=18*mm,
        title="Portfolio Health Check"
    )
    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]; H1.textColor = colors.HexColor("#1F3B63")
    H2 = styles["Heading2"]; H2.textColor = colors.HexColor("#1F3B63")
    body = styles["BodyText"]

    story = []

    # Cover / Summary
    story.append(Paragraph("Portfolio Health Check", H1))
    story.append(Spacer(1, 4*mm))
    meta = {
        "Generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Template Type": template_type,
    }
    if "metrics" in results:
        # format selected metrics
        m = results["metrics"]
        pretty = {}
        for k, v in m.items():
            if isinstance(v, (int, float)):
                pretty[k] = f"{v:,.2f}" if isinstance(v, float) else f"{v:,d}"
            else:
                pretty[k] = str(v)
        meta.update(pretty)
    story.append(_kv_table(meta))
    story.append(Spacer(1, 6*mm))

    # Add charts by template
    def add_fig_section(title: str, key: str):
        if key in figs and figs[key] is not None:
            story.append(Paragraph(title, H2))
            img = _img_flowable(_fig_to_png_bytes(figs[key]))
            story.append(img)
            story.append(Spacer(1, 6*mm))

    if template_type == "PortfolioMaster":
        add_fig_section("By Asset Class", "pm_asset_pie")
        add_fig_section("By Sub-Asset", "pm_subasset_pie")
        add_fig_section("Currency", "pm_currency_bar")
        add_fig_section("Liquidity", "pm_liquidity_bar")

    elif template_type == "EquityAssetList":
        add_fig_section("Equity by Sector", "eq_sector_pie")
        add_fig_section("Equity by Region", "eq_region_pie")
        add_fig_section("Top Positions (by MV)", "eq_top_bar")

    elif template_type == "FixedIncomeAssetList":
        add_fig_section("Fixed Income by Rating", "fi_rating_pie")
        add_fig_section("Maturity Ladder", "fi_maturity_bar")
        add_fig_section("Duration Buckets", "fi_duration_bar")

    # Build with header on all pages
    def _on_page(canvas, doc):
        _header(canvas, doc, logo_path, "Parkview Group — Sustaining Wealth")

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buf.seek(0)
    return buf.read()
