# core/backend/portfolio_compare.py
import pandas as pd
from .portfolio_backtest import backtest_portfolio

def compare_two_portfolios(p1, p2, period="5y"):
    s1 = backtest_portfolio(p1["symbols"], p1["weights"], period=period)
    s2 = backtest_portfolio(p2["symbols"], p2["weights"], period=period)

    if s1 is None or s2 is None:
        return None

    df = pd.concat(
        [s1.rename(p1["name"]), s2.rename(p2["name"])],
        axis=1
    ).dropna()

    return df
