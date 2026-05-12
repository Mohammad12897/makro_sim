#core/country/country_compare.py

import pandas as pd
import numpy as np
from core.data.market_data import load_asset_series

def compute_country_metrics(ticker):
    data = load_asset_series(ticker)
    returns = pd.Series(data["returns"], index=data["dates"])

    total_return = (1 + returns).prod() - 1
    volatility = returns.std() * np.sqrt(252)
    max_dd = ((1 + returns).cumprod() / (1 + returns).cumprod().cummax() - 1).min()

    return {
        "Land/Index": ticker,
        "Rendite": total_return,
        "Volatilität": volatility,
        "Max Drawdown": max_dd,
    }

def compare_countries(tickers):
    rows = [compute_country_metrics(t) for t in tickers]
    return pd.DataFrame(rows)
