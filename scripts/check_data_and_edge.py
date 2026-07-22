from pathlib import Path
import sys
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("check_csv")

from risk_dashboard.core.holdings import load_holdings_with_fallback
from risk_dashboard.ui.profiles_ui import load_price_data

HOLDINGS_DIR = PROJECT_ROOT / "risk_dashboard" / "data" / "holdings"

import pandas as pd
from risk_dashboard.data_utils import fetch_prices_quiet
print(fetch_prices_quiet(['EXS1.DE'], start='2020-01-01').head())

print("****************************************************************")

print(fetch_prices_quiet(['EXS1.DE','EXS2.DE'], start='2020-01-01').tail())

print("****************************************************************")


import yfinance as yf
#df = yf.download(['EXS1.DE','EXS2.DE'], start='2020-01-01', group_by='ticker')
#print(df.columns)
#print(df.head())
