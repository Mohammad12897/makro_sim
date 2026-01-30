# core/analysis/market_data.py
import datetime as dt
from dataclasses import dataclass
from typing import Optional, Dict

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class AssetMetrics:
    ticker: str
    name: str
    region: str
    asset_class: str
    perf_1y: Optional[float]
    perf_5y: Optional[float]
    volatility: Optional[float]
    sharpe: Optional[float]
    max_drawdown: Optional[float]
    beta: Optional[float]
    ter: Optional[float] = None


def _get_history(ticker: str, years: int = 5) -> pd.Series:
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * years)
    data = yf.Ticker(ticker).history(start=start, end=end)
    if data is None or data.empty:
        return pd.Series(dtype=float)
    return data["Adj Close"].dropna()


def _calc_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


def _annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    return returns.std() * np.sqrt(periods_per_year)


def _sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    if returns.empty:
        return np.nan
    excess = returns - risk_free_rate / periods_per_year
    vol = _annualized_volatility(excess, periods_per_year)
    if vol == 0:
        return np.nan
    return (excess.mean() * periods_per_year) / vol


def _max_drawdown(prices: pd.Series) -> float:
    if prices.empty:
        return np.nan
    roll_max = prices.cummax()
    drawdown = prices / roll_max - 1.0
    return drawdown.min()


def _beta(prices: pd.Series, benchmark: pd.Series) -> float:
    if prices.empty or benchmark.empty:
        return np.nan
    r_a = _calc_returns(prices)
    r_b = _calc_returns(benchmark)
    df = pd.concat([r_a, r_b], axis=1).dropna()
    if df.shape[0] < 10:
        return np.nan
    cov = np.cov(df.iloc[:, 0], df.iloc[:, 1])[0, 1]
    var = np.var(df.iloc[:, 1])
    if var == 0:
        return np.nan
    return cov / var


def get_asset_metrics(entry: Dict, benchmark_ticker: str = "^GSPC") -> AssetMetrics:
    ticker = entry["ticker"]
    name = entry.get("name", ticker)
    region = entry.get("region", "Global")
    asset_class = entry.get("asset_class", "Equity")

    prices_5y = _get_history(ticker, years=5)
    prices_1y = prices_5y[prices_5y.index >= (prices_5y.index.max() - pd.Timedelta(days=365))]

    def perf(series: pd.Series) -> Optional[float]:
        if series.empty:
            return None
        return float(series.iloc[-1] / series.iloc[0] - 1.0)

    perf_1y = perf(prices_1y)
    perf_5y = perf(prices_5y)
    rets = _calc_returns(prices_5y)
    vol = float(_annualized_volatility(rets)) if not rets.empty else None
    sharpe = float(_sharpe_ratio(rets)) if not rets.empty else None
    mdd = float(_max_drawdown(prices_5y)) if not prices_5y.empty else None

    try:
        bench_prices = _get_history(benchmark_ticker, years=5)
        b = float(_beta(prices_5y, bench_prices))
    except Exception:
        b = None

    ter = entry.get("ter")

    return AssetMetrics(
        ticker=ticker,
        name=name,
        region=region,
        asset_class=asset_class,
        perf_1y=perf_1y,
        perf_5y=perf_5y,
        volatility=vol,
        sharpe=sharpe,
        max_drawdown=mdd,
        beta=b,
        ter=ter,
    )


def metrics_to_row(m: AssetMetrics) -> Dict:
    def pct(x):
        return None if x is None or np.isnan(x) else round(100 * x, 2)

    return {
        "Ticker": m.ticker,
        "Name": m.name,
        "Region": m.region,
        "Asset-Klasse": m.asset_class,
        "1Y %": pct(m.perf_1y),
        "5Y %": pct(m.perf_5y),
        "Volatilität %": pct(m.volatility),
        "Sharpe": None if m.sharpe is None or np.isnan(m.sharpe) else round(m.sharpe, 2),
        "Max Drawdown %": pct(m.max_drawdown),
        "Beta": None if m.beta is None or np.isnan(m.beta) else round(m.beta, 2),
        "TER %": m.ter,
    }
