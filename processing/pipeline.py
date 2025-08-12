import pandas as pd
import duckdb
from .schema import PositionsSchema, BusinessRules

def read_template(xls_file) -> dict[str, pd.DataFrame]:
    # keep_default_na=False prevents strings like "NA" being turned into NaN
    with pd.ExcelFile(xls_file) as x:
        sheets = {s: x.parse(s, keep_default_na=False) for s in x.sheet_names}

    # Optional, tolerant version check
    tv = None
    if "Meta" in sheets and not sheets["Meta"].empty:
        tv = str(sheets["Meta"].iloc[0, 0]).strip()
    if tv and not tv.startswith("Template v1"):
        raise ValueError(f"Incompatible template version: {tv}")

    # Normalize expected sheet if present
    pos = next((sheets[k] for k in sheets if k.lower() == "positions"), None)
    if pos is not None:
        # trim headers
        pos.columns = [str(c).strip() for c in pos.columns]
        # normalize strings
        for c in ["AssetClass", "Region", "Currency"]:
            if c in pos.columns:
                pos[c] = pos[c].astype(str).str.strip()
        if "Currency" in pos.columns:
            pos["Currency"] = pos["Currency"].str.upper().str[:3]
        # normalize numerics
        for c in ["MarketValue", "Weight"]:
            if c in pos.columns:
                pos[c] = pd.to_numeric(pos[c], errors="coerce").astype(float)
        if "Date" in pos.columns:
            pos["Date"] = pd.to_datetime(pos["Date"], errors="coerce")
        sheets["Positions"] = pos

    return sheets

def validate_positions(df: pd.DataFrame) -> list[dict]:
    errors = []
    try:
        PositionsSchema.validate(df, lazy=True)
    except Exception as e:
        for err in getattr(e, "failure_cases", pd.DataFrame()).to_dict("records"):
            errors.append({"column": err.get("column"), "index": err.get("index"), "failure": err.get("failure_case")})
    for rule in BusinessRules:
        ok, msg = rule(df)
        if not bool(ok):
            errors.append({"column": None, "index": None, "failure": msg})
    return errors

def transform(df: pd.DataFrame) -> dict:
    con = duckdb.connect()
    con.register("pos", df)
    alloc_asset = con.execute("""
        SELECT AssetClass, SUM(Weight) AS Weight
        FROM pos GROUP BY 1 ORDER BY 2 DESC
    """).df()

    alloc_region = con.execute("""
        SELECT Region, SUM(Weight) AS Weight
        FROM pos GROUP BY 1 ORDER BY 2 DESC
    """).df()

    currency_exp = con.execute("""
        SELECT Currency, SUM(Weight) AS Weight
        FROM pos GROUP BY 1 ORDER BY 2 DESC
    """).df()

    # Example liquidity/risk/fees placeholders (extend later)
    metrics = {
        "gross_exposure": float(df["Weight"].sum()),
        "n_positions": int(df.shape[0]),
    }
    return {
        "alloc_asset": alloc_asset,
        "alloc_region": alloc_region,
        "currency_exp": currency_exp,
        "metrics": metrics,
    }



