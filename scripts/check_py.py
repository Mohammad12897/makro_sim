
import pandas as pd
df = pd.read_csv("risk_dashboard/data/macro_df.csv", index_col=0, parse_dates=True)
print(df.shape, df.columns.tolist(), df.head(3).to_dict(orient='records'))

print("***********************************")

import pandas as pd
p = r"C:\Projects\makro_sim\risk_dashboard\data\macro_df.csv"
df = pd.read_csv(p, index_col=0, parse_dates=True)
print("shape:", df.shape)
print("columns:", df.columns.tolist())
print(df.head(3).to_dict(orient='records'))
print("***********************************")

import ast, pathlib, sys
for p in pathlib.Path("risk_dashboard").rglob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print("SyntaxError in", p, e)
        sys.exit(1)
print("OK: alle Python-Dateien parsebar")
print("***********************************")

from pathlib import Path
b = Path("risk_dashboard/config/classify_keys.py").read_bytes()
print("NUL present:", b.find(b'\x00')!=-1)
print(b[:200].hex())