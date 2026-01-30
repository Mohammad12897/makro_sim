# core/analysis/stock_compare.py
from typing import Dict
import pandas as pd
import yfinance as yf
import numpy as np

from core.analysis.market_data import _get_history, _calc_returns, _annualized_volatility, _sharpe_ratio, _max_drawdown


def _basic_metrics(ticker: str) -> Dict:
    prices = _get_history(ticker, years=5)
    if prices.empty:
        return {"ticker": ticker, "ok": False}

    rets = _calc_returns(prices)
    one_year = prices[prices.index >= (prices.index.max() - pd.Timedelta(days=365))]

    def perf(series: pd.Series):
        if series.empty:
            return np.nan
        return float(series.iloc[-1] / series.iloc[0] - 1.0)

    return {
        "ticker": ticker,
        "ok": True,
        "perf_1y": perf(one_year),
        "perf_5y": perf(prices),
        "vol": _annualized_volatility(rets) if not rets.empty else np.nan,
        "sharpe": _sharpe_ratio(rets) if not rets.empty else np.nan,
        "mdd": _max_drawdown(prices),
        "prices": prices,
    }


def _correlation(a: pd.Series, b: pd.Series) -> float:
    df = pd.concat([a, b], axis=1).dropna()
    if df.shape[0] < 10:
        return np.nan
    return float(df.corr().iloc[0, 1])


def stock_compare(t1: str, t2: str) -> str:
    m1 = _basic_metrics(t1)
    m2 = _basic_metrics(t2)

    if not m1["ok"] or not m2["ok"]:
        return f"Mindestens einer der Ticker ist ungültig oder hat keine Daten: {t1}, {t2}"

    corr = _correlation(m1["prices"], m2["prices"])

    def fmt_pct(x):
        return "n/a" if x is None or np.isnan(x) else f"{x*100:,.2f}%"

    def fmt(x):
        return "n/a" if x is None or np.isnan(x) else f"{x:,.2f}"

    lines = []
    lines.append(f"### Vergleich: {t1} vs {t2}\n")
    lines.append("| Kennzahl | {0} | {1} |".format(t1, t2))
    lines.append("|----------|------|------|")
    lines.append(f"| 1Y Rendite | {fmt_pct(m1['perf_1y'])} | {fmt_pct(m2['perf_1y'])} |")
    lines.append(f"| 5Y Rendite | {fmt_pct(m1['perf_5y'])} | {fmt_pct(m2['perf_5y'])} |")
    lines.append(f"| Volatilität | {fmt_pct(m1['vol'])} | {fmt_pct(m2['vol'])} |")
    lines.append(f"| Sharpe Ratio | {fmt(m1['sharpe'])} | {fmt(m2['sharpe'])} |")
    lines.append(f"| Max Drawdown | {fmt_pct(m1['mdd'])} | {fmt_pct(m2['mdd'])} |")
    lines.append(f"| Korrelation | {fmt(corr)} | – |")

    # einfache Empfehlung: höhere Sharpe gewinnt, bei ähnlicher Sharpe: höhere 5Y-Rendite
    rec = ""
    s1, s2 = m1["sharpe"], m2["sharpe"]
    if not np.isnan(s1) and not np.isnan(s2):
        if s1 > s2 + 0.1:
            rec = f"**Tendenz:** {t1} hat die bessere risikobereinigte Rendite (Sharpe)."
        elif s2 > s1 + 0.1:
            rec = f"**Tendenz:** {t2} hat die bessere risikobereinigte Rendite (Sharpe)."
        else:
            if m1["perf_5y"] > m2["perf_5y"]:
                rec = f"**Tendenz:** Beide ähnlich im Risiko, {t1} hat leicht bessere Langfrist-Rendite."
            else:
                rec = f"**Tendenz:** Beide ähnlich im Risiko, {t2} hat leicht bessere Langfrist-Rendite."
    lines.append("\n" + rec)

    return "\n".join(lines)
