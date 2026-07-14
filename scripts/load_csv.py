from pathlib import Path
import pandas as pd


p = "risk_dashboard/data/holdings/CSPX.L.csv"
for sep in [",",";","\t"]:
    try:
        df = pd.read_csv(p, sep=sep, nrows=5, encoding="utf-8")
        print("sep", sep, "columns:", df.columns.tolist())
    except Exception as e:
        print("sep", sep, "failed:", e)

print("------------------------------")

df = pd.read_csv("risk_dashboard/data/holdings/CSPX.L.csv", sep=",", encoding="utf-8")
print(df.columns)
if "weight_in_etf" in df.columns:
    print("sum weights:", df["weight_in_etf"].sum())
else:
    print("Erwarte Spalte 'weight_in_etf' nicht gefunden")

print("------------------------------")

# importiere die loader-funktion falls vorhanden, z.B.:
# from risk_dashboard.core.holdings import load_ishares_csv

p = Path("risk_dashboard/data/holdings/CSPX.L.csv")
df = pd.read_csv(p)
print("columns:", df.columns.tolist())
print("sample:\n", df.head().to_string(index=False))
print("sum weight:", df["weight_in_etf"].astype(float).sum())

# Falls du eine loader-funktion hast, rufe sie direkt:
# ok, msg = load_ishares_csv(p)   # anpassen an deinen API
# print("loader ok:", ok, "msg:", msg)
print("------------------------------")

p = Path("risk_dashboard/data/price_data.csv")
print("exists:", p.exists())
df = pd.read_csv(p, index_col=0, parse_dates=True)
print("shape:", df.shape)
print("columns:", list(df.columns)[:10])
print(df.head())

print("------------------------------")
p = Path("risk_dashboard/data/portfolio.csv")
print("exists:", p.exists())
df = pd.read_csv(p, nrows=5)
print(df)
