# scripts/debug_backtest.py
from pathlib import Path
import sys
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("check_csv")

from risk_dashboard.core.utils import detect_price_format,  extract_close_series, compute_market_value_from_holdings, prepare_prices_for_backtest
from risk_dashboard.ui.profiles_ui import load_price_data
from risk_dashboard.core.weights import compute_abs_weights

# Beispiel-Holdings
hdf = pd.DataFrame([
    {"ticker":"AAPL", "weight_in_etf":0.3},
    {"ticker":"MSFT", "weight_in_etf":0.3},
    {"ticker":"NVDA", "weight_in_etf":0.2},
    {"ticker":"AMZN", "weight_in_etf":0.2},
])

portfolio_value = 100000.0

# Beispiel-Preise
prices = pd.DataFrame({
    "AAPL":[150,151],
    "MSFT":[300,305],
    "NVDA":[400,410],
    "AMZN":[100,102],
}, index=pd.to_datetime(["2026-07-01","2026-07-02"]))


pc = extract_close_series(prices)

hdf2, method = compute_market_value_from_holdings(hdf, pc, portfolio_value)
hdf_out = compute_abs_weights(hdf2, portfolio_value)
weights_for_backtest = (hdf_out.set_index("ticker")["abs_weight"] * portfolio_value).to_dict()


print("sum market_value:", hdf2["market_value"].sum(), "expected:", portfolio_value)
print("sum abs_weight:", hdf_out["abs_weight"].sum())
print("last prices:", pc.iloc[-1].to_dict())
print("weights sample:", list(weights_for_backtest.items())[:10])



print("**********************************************************************************")
print("method:*****************************************************", method)
print("*************",method, hdf2[["ticker","market_value"]].head())
print("*************",hdf2)
print("*************",pc.columns[:10], pc.index.dtype)
prices = prepare_prices_for_backtest(hdf, PROJECT_ROOT, load_price_data)

assert prices is not None, "prepare_prices_for_backtest returned None"
print("*************prepare_prices_for_backtest -> shape:", prices.shape)
# direkt nach prepare_prices_for_backtest
print("*************prices.shape:", prices.shape)
print("*************prices.columns:", list(prices.columns)[:50])
print("*************prices.index:", prices.index[:5])
test = load_price_data(["AAPL","MSFT"])
print("*************test shape:", getattr(test, "shape", None))
