from pathlib import Path
import sys
import logging
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
Path("risk_dashboard/data/backtests").mkdir(parents=True, exist_ok=True)
print("done")

print("--------------------------------------------------")
import site, os
print("user site:", site.getusersitepackages())
print("sys.path:")
import sys
print("\n".join(sys.path))

print("--------------------------------------------------")
import inspect
import risk_dashboard.core.backtest as b
print("file:", b.__file__)
print("---- source start ----")
print(inspect.getsource(b))
print("---- source end ----")
print("--------------------------------------------------")
import risk_dashboard.core.backtest as b
print("backtest module file:", b.__file__)
