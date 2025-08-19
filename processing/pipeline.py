import pandas as pd
from .schema import (
    PortfolioMasterSchema,
    EquityAssetListSchema,
    FixedIncomeAssetListSchema,
    business_rules,
)

# ------------------------------------------------------
# IO & detection
# ------------------------------------------------------
def read_workbook(xls_file):
    """Return (sheets_dict, meta_string). Keep 'NA' as text."""
    with pd.ExcelFile(xls_file) as x:
        sheets = {s: x.parse(s, keep_default_na=False) for s in x.sheet_names}
    meta_str = None
    if "Meta" in sheets and not sheets["Meta"].empty:
        meta_str = str(sheets["Meta"].iloc[0, 0]).strip()
    # basic normalization
    for k, df in list(sheets.items()):
        df.columns = [str(c).strip() for c in df.columns]
    return sheets, meta_str

def detect_template_type(sheets, meta_str):
    if meta_str:
        if "EquityAssetList" in meta_str:
            return "EquityAssetList"
        if "FixedIncomeAssetList" in meta_str:
            return "FixedIncomeAssetList"
        if "PortfolioMaster" in meta_str or "Pastor" in meta_str:
            return "PortfolioMaster"
    names = [s.lower() for s in sheets]
    if "equityassetlist" in names: return "EquityAssetList"
    if "fixedincomeassetlist" in names: return "FixedIncomeAssetList"
    if "portfoliomaster" in names or "pastor" in names: return "PortfolioMaster"
    # default
    return "PortfolioMaster"

def get_required_sheet_for_type(tmpl_type):
    return {
        "PortfolioMaster": "PortfolioMaster",   # will also accept 'Pastor' via fallback in app
        "EquityAssetList": "EquityAssetList",
        "FixedIncomeAssetList": "FixedIncomeAssetList",
    }[tmpl_type]

# ------------------------------------------------------
# Validation
# ------------------------------------------------------
def _schema_for_type(tmpl_type):
    return {
        "PortfolioMaster": PortfolioMasterSchema,
        "EquityAssetList": EquityAssetListSchema,
        "FixedIncomeAssetList": FixedIncomeAssetListSchema,
    }[tmpl_type]

def validate_df(df: pd.DataFrame, tmpl_type: str) -> list[dict]:
    errors = []
    # type coercion/validation
    try:
        _schema_for_type(tmpl_type).validate(df, lazy=True)
    except Exception as e:
        fc = getattr(e, "failure_cases", pd.DataFrame())
        if isinstance(fc, pd.DataFrame) and not fc.empty:
            errors.extend(
                {"column": r.get("column"), "index": r.get("index"), "failure": r.get("failure_case")}
                for r in fc.to_dict("records")
            )
    # business rules
    for ok, msg in business_rules(df, tmpl_type):
        if not bool(ok):
            errors.append({"column": None, "index": None, "failure": msg})
    return errors

# ------------------------------------------------------
# Transforms for each template
# ------------------------------------------------------
def transform_results(df: pd.DataFrame, tmpl_type: str) -> dict:
    if tmpl_type == "PortfolioMaster":
        out = {}
        df["USD Total"] = pd.to_numeric(df.get("USD Total"), errors="coerce").fillna(0.0)
        out["by_asset_class"] = (
            df.groupby("Asset Class", as_index=False)["USD Total"].sum().sort_values("USD Total", ascending=False)
        )
        out["by_sub_asset"] = (
            df.groupby("Sub Asset Class", as_index=False)["USD Total"].sum().sort_values("USD Total", ascending=False)
        )
        if "FX" in df.columns:
            out["by_fx"] = (
                df.groupby("FX", as_index=False)["USD Total"].sum().sort_values("USD Total", ascending=False)
            )
        else:
            out["by_fx"] = pd.DataFrame(columns=["FX", "USD Total"])
        if "Liquid/Illiquid" in df.columns:
            out["by_liquidity"] = (
                df.groupby("Liquid/Illiquid", as_index=False)["USD Total"].sum().sort_values("USD Total", ascending=False)
            )
        else:
            out["by_liquidity"] = pd.DataFrame(columns=["Liquid/Illiquid", "USD Total"])
        out["top_assets"] = df.sort_values("USD Total", ascending=False).head(15)[
            ["Asset Class","Sub Asset Class","Manager","Asset","USD Total"]
        ]
        out["metrics"] = {
            "n_rows": int(df.shape[0]),
            "usd_total_sum": float(df["USD Total"].sum()),
        }
        out["template_type"] = tmpl_type
        return out

    if tmpl_type == "EquityAssetList":
        out = {}
        df["Weight %"] = pd.to_numeric(df.get("Weight %"), errors="coerce").fillna(0.0)
        df["Market Value (USD)"] = pd.to_numeric(df.get("Market Value (USD)"), errors="coerce").fillna(0.0)
        out["by_sector"] = (
            df.groupby("Sector (GICS)", as_index=False)["Weight %"].sum().sort_values("Weight %", ascending=False)
        )
        if "Region" in df.columns:
            out["by_region"] = (
                df.groupby("Region", as_index=False)["Weight %"].sum().sort_values("Weight %", ascending=False)
            )
        else:
            out["by_region"] = pd.DataFrame(columns=["Region","Weight %"])
        out["top_positions"] = df.sort_values("Market Value (USD)", ascending=False).head(20)[
            ["Asset (Security Name)","Ticker","Sector (GICS)","Region","Market Value (USD)","Weight %"]
        ]
        out["metrics"] = {
            "n_rows": int(df.shape[0]),
            "mv_sum": float(df["Market Value (USD)"].sum()),
            "w_sum": float(df["Weight %"].sum()),
        }
        out["template_type"] = tmpl_type
        return out

    if tmpl_type == "FixedIncomeAssetList":
        out = {}
        df["Weight %"] = pd.to_numeric(df.get("Weight %"), errors="coerce").fillna(0.0)
        df["Market Value (USD)"] = pd.to_numeric(df.get("Market Value (USD)"), errors="coerce").fillna(0.0)
        df["Modified Duration"] = pd.to_numeric(df.get("Modified Duration"), errors="coerce").fillna(0.0)
        # Rating buckets
        rating_col = "Rating (S&P/Moody's/Fitch)" if "Rating (S&P/Moody's/Fitch)" in df.columns else "Rating"
        if rating_col in df.columns:
            out["by_rating"] = (
                df.groupby(rating_col, as_index=False)["Weight %"].sum().rename(columns={rating_col:"Rating"})
                .sort_values("Weight %", ascending=False)
            )
        else:
            out["by_rating"] = pd.DataFrame(columns=["Rating","Weight %"])
        # Maturity buckets
        now = pd.Timestamp.today().normalize()
        if "Maturity Date" in df.columns:
            y = ((pd.to_datetime(df["Maturity Date"], errors="coerce") - now).dt.days / 365.25).fillna(0)
            def mat_bucket(yrs):
                if yrs < 1: return "<1y"
                if yrs < 3: return "1–3y"
                if yrs < 5: return "3–5y"
                if yrs < 7: return "5–7y"
                if yrs < 10: return "7–10y"
                return "10y+"
            df["_mat_bucket"] = y.apply(mat_bucket)
            out["maturity_buckets"] = (
                df.groupby("_mat_bucket", as_index=False)["Weight %"].sum().rename(columns={"_mat_bucket":"Bucket"})
                .sort_values("Weight %", ascending=False)
            )
        else:
            out["maturity_buckets"] = pd.DataFrame(columns=["Bucket","Weight %"])
        # Duration buckets (by Modified Duration)
        def dur_bucket(d):
            if d < 1: return "<1"
            if d < 3: return "1–3"
            if d < 5: return "3–5"
            if d < 7: return "5–7"
            if d < 10: return "7–10"
            return "10+"
        df["_dur_bucket"] = df["Modified Duration"].apply(dur_bucket)
        out["duration_buckets"] = (
            df.groupby("_dur_bucket", as_index=False)["Weight %"].sum().rename(columns={"_dur_bucket":"Bucket"})
            .sort_values("Weight %", ascending=False)
        )
        # Metrics
        mv = df["Market Value (USD)"].sum()
        dur_wt_avg = (df["Modified Duration"] * df["Weight %"].fillna(0)/100.0).sum() if df["Weight %"].sum() else 0.0
        out["metrics"] = {
            "n_rows": int(df.shape[0]),
            "mv_sum": float(mv),
            "w_sum": float(df["Weight %"].sum()),
            "dur_wt_avg": float(dur_wt_avg),
        }
        out["template_type"] = tmpl_type
        return out

    # fallback
    return {"template_type": tmpl_type, "metrics": {"n_rows": int(df.shape[0])}}

