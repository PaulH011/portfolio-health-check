import io
import pandas as pd
import xlsxwriter

def build_report_xlsx(results: dict) -> bytes:
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    fmt_pct = wb.add_format({"num_format":"0.00%"})
    fmt_hdr = wb.add_format({"bold": True, "bg_color": "#F2F2F2"})

    # Summary
    ws = wb.add_worksheet("Summary")
    ws.write_row(0, 0, ["Metric","Value"], fmt_hdr)
    r=1
    for k,v in results["metrics"].items():
        ws.write(r,0,k); ws.write(r,1,v); r+=1

    # Allocation by AssetClass
    def add_table_chart(name, df, category_col, value_col, chart_type="column"):
        w = wb.add_worksheet(name)
        w.write_row(0,0,df.columns.tolist(), fmt_hdr)
        for i,row in enumerate(df.itertuples(index=False), start=1):
            for j, val in enumerate(row):
                w.write(i,j,val)
        # chart
        ch = wb.add_chart({"type": chart_type})
        nrows = len(df)
        ch.add_series({
            "name": name,
            "categories": [name, 1, 0, nrows, 0],
            "values": [name, 1, 1, nrows, 1],
            "data_labels": {"value": True},
        })
        ch.set_title({"name": name})
        w.insert_chart(1, 3, ch, {"x_scale": 1.1, "y_scale": 1.1})

    add_table_chart("Alloc_Asset", results["alloc_asset"], "AssetClass", "Weight", "column")
    add_table_chart("Alloc_Region", results["alloc_region"], "Region", "Weight", "bar")
    add_table_chart("Currency_Exposure", results["currency_exp"], "Currency", "Weight", "column")

    wb.close()
    output.seek(0)
    return output.read()

def build_validation_report(errors: list[dict]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xl:
        df = pd.DataFrame(errors) if errors else pd.DataFrame(columns=["column","index","failure"])
        df.to_excel(xl, index=False, sheet_name="Validation")
    buf.seek(0)
    return buf.read()

def build_pdf_from_html(html: str) -> bytes:
    # simple summary PDF (optional)
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
