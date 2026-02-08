# core/backend/portfolio_compare.py
import pandas as pd
from .portfolio_backtest import backtest_portfolio

def compare_two_portfolios(p1, p2, period="5y"):
    df1 = backtest_portfolio(p1["symbols"], p1["weights"], period=period)
    df2 = backtest_portfolio(p2["symbols"], p2["weights"], period=period)
    if df1 is None or df2 is None:
        return None
    joined = pd.concat(
        [df1["Portfolio"].rename(p1["name"]), df2["Portfolio"].rename(p2["name"])],
        axis=1
    ).dropna()
    return joined
