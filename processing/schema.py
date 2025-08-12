import pandera as pa
from pandera import Column, Check, DataFrameSchema

PositionsSchema = DataFrameSchema({
    "PortfolioID": Column(str, nullable=False, coerce=True),
    "Date": Column(pa.DateTime, nullable=False, coerce=True),
    "AssetName": Column(str, nullable=False, coerce=True),
    "AssetClass": Column(str, checks=Check.isin(["Equities","Fixed Income","Alternatives","Cash"]), nullable=False, coerce=True),
    "Region": Column(str, checks=Check.isin(["NA","EU","UK","APAC","EM","Global"]), nullable=False, coerce=True),
    "Currency": Column(str, checks=Check.str_length(3,3), nullable=False, coerce=True),
    "MarketValue": Column(float, checks=Check.ge(0.0), nullable=False, coerce=True),
    "Weight": Column(float, checks=Check.ge(0.0), nullable=False, coerce=True),
})

BusinessRules = [
    lambda df: (abs(df["Weight"].sum() - 100.0) <= 0.2, "Weights do not sum to ~100%"),
]
