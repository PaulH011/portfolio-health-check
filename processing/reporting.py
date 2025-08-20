import io
import pandas as pd

def generate_excel_report(df: pd.DataFrame) -> bytes:
    """
    Generate Excel report from validated dataframe.
    Returns Excel file as bytes for Streamlit download_button.
    """

    output = io.BytesIO()

    # Write to Excel
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Main data
        df.to_excel(writer, sheet_name="Data", index=False)

        # Simple summary tab if fields exist
        summary = {}
        if "Weight %" in df.columns:
            summary["Total Weight %"] = [df["Weight %"].sum()]
        if "USD Total" in df.columns:
            summary["Total USD"] = [df["USD Total"].sum()]
        if "Sector" in df.columns:
            sector_alloc = df.groupby("Sector")["Weight %"].sum().reset_index()
            sector_alloc.to_excel(writer, sheet_name="SectorAlloc", index=False)
        if "Asset Class" in df.columns:
            asset_alloc = df.groupby("Asset Class")["USD Total"].sum().reset_index()
            asset_alloc.to_excel(writer, sheet_name="AssetAlloc", index=False)

        if summary:
            pd.DataFrame(summary).to_excel(writer, sheet_name="Summary", index=False)

        # Auto-adjust column widths
        for sheet_name, worksheet in writer.sheets.items():
            for i, col in enumerate(df.columns):
                col_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, col_width)

    return output.getvalue()
