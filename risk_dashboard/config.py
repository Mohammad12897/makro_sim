# risk_dashboard/config.py
from datetime import date
import pandas as pd

# Strings als Canonical Defaults (lesbar in Configs)
DEFAULT_START_STR = "2016-01-01"
DEFAULT_END_STR = date.today().isoformat()

# Pandas Timestamps für interne Verwendung
DEFAULT_START = pd.to_datetime(DEFAULT_START_STR)
DEFAULT_END = pd.to_datetime(DEFAULT_END_STR)
