import pandas as pd
from pathlib import Path

p = Path("data/price_data.csv")
print("price_data exists:", p.exists())
if p.exists():
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    print("price_data shape:", df.shape)
    print(df.columns[:10])

holdings = list(Path("data/holdings").glob("*.csv"))
print("holdings files:", [h.name for h in holdings])
