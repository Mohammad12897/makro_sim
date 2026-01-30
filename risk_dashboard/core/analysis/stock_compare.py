# core/analysis/stock_compare.py
import numpy as np
from core.analysis.market_data import get_history, calc_returns, annual_vol, sharpe_ratio, max_drawdown

def stock_compare(t1, t2):
    p1 = get_history(t1)
    p2 = get_history(t2)

    if p1.empty or p2.empty:
        return f"Keine Daten für {t1} oder {t2}"

    r1 = calc_returns(p1)
    r2 = calc_returns(p2)

    def perf(series):
        if series.empty:
            return np.nan
        return float(series.iloc[-1] / series.iloc[0] - 1)

    one_year_1 = p1[p1.index >= (p1.index.max() - pd.Timedelta(days=365))]
    one_year_2 = p2[p2.index >= (p2.index.max() - pd.Timedelta(days=365))]

    corr = np.corrcoef(r1.align(r2, join="inner")[0].dropna(),
                       r2.align(r1, join="inner")[0].dropna())[0, 1]

    md = f"""
### Vergleich: {t1} vs {t2}

| Kennzahl | {t1} | {t2} |
|----------|------|------|
| 1Y Rendite | {perf(one_year_1)*100:.2f}% | {perf(one_year_2)*100:.2f}% |
| 5Y Rendite | {perf(p1)*100:.2f}% | {perf(p2)*100:.2f}% |
| Volatilität | {annual_vol(r1)*100:.2f}% | {annual_vol(r2)*100:.2f}% |
| Sharpe Ratio | {sharpe_ratio(r1):.2f} | {sharpe_ratio(r2):.2f} |
| Max Drawdown | {max_drawdown(p1)*100:.2f}% | {max_drawdown(p2)*100:.2f}% |
| Korrelation | {corr:.2f} | – |

"""

    if sharpe_ratio(r1) > sharpe_ratio(r2):
        md += f"**Empfehlung:** {t1} hat die bessere risikobereinigte Rendite."
    else:
        md += f"**Empfehlung:** {t2} hat die bessere risikobereinigte Rendite."

    return md
