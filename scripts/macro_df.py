# scripts/macro_df.py
from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


p = Path("risk_dashboard/data/macro_df.csv")
if not p.exists():
    df = pd.DataFrame({
        "date": pd.date_range("2010-01-01", periods=10, freq="A"),
        "gdp": 0.0,
        "volatility": 0.0
    }).set_index("date")
    df.to_csv(p)


from pathlib import Path
p = Path("risk_dashboard/data/macro_df.csv")
print("macro exists:", p.exists())
