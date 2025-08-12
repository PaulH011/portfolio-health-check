import pandas as pd
from .schema import PositionsSchema, BusinessRules

def read_template(xls_file) -> dict[str, pd.DataFrame]:
    with pd.ExcelFile(xls_file) as x:
        sheets = {s: x.parse(s) for s in x.sheet_names}
    # Tolerant version check: only enforce if Meta exists and has a value
    tv = None
    if "Meta" in sheets and not sheets["Meta"].empty:
        tv = str(sheets["Meta"].iloc[0, 0]).strip()
    if tv and not tv.startswith("Template v1"):
        raise ValueError(f"Incompatible template version: {tv}")
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

