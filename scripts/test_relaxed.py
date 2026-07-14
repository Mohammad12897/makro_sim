from pathlib import Path
import sys
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("check_csv")

from risk_dashboard.core.holdings import try_relaxed_holdings

import inspect
from risk_dashboard.core.backtest import run_all_etf_backtests
print("signature:", inspect.signature(run_all_etf_backtests))

print("--------------------------------------------------")

import importlib, inspect
m = importlib.import_module("risk_dashboard.core.helpers")
print("module file:", getattr(m, "__file__", None))
print("has classify_etf:", hasattr(m, "classify_etf"))
print("callable:", callable(getattr(m, "classify_etf", None)))


print("--------------------------------------------------")


ok, res = try_relaxed_holdings(Path("risk_dashboard/data/holdings/CSPX.L.csv"))
print("ok:", ok)
if ok:
    print(res.head())
else:
    print("reason:", res)


print("--------------------------------------------------")
