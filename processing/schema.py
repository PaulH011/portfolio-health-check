import pandera as pa
from pandera import Column, Check, DataFrameSchema

# Example "Positions" sheet schema — adapt to your template
PositionsSchema = DataFrameSchema({
    "PortfolioID": Column(str, nullable=False),
    "Date": Column(pa.DateTime, nullable=False),
    "AssetName": Column(str, nullable=False),
    "AssetClass": Column(str, checks=Check.isin(["Equities","Fixed Income","Alternatives","Cash"]), nullable=False),
    "Region": Column(str, checks=Check.isin(["NA","EU","UK","APAC","EM","Global"]), nullable=False),
    "Currency": Column(str, checks=Check.str_length(3,3), nullable=False),
    "MarketValue": Column(float, checks=Check.ge(0.0), nullable=False),
    "Weight": Column(float, checks=Check.ge(0.0), nullable=False),
})

BusinessRules = [
    lambda df: (abs(df["Weight"].sum() - 100.0) <= 0.2, "Weights do not sum to ~100%"),
    lambda df: (df.groupby("Currency")["Weight"].sum().le(100.0).all(), "Currency weights exceed 100% per currency"),
]
