# tests/test_holdings.py
import pandas as pd
from risk_dashboard.handlers import compute_market_value_from_holdings

prices = pd.DataFrame({'CSPX.L':[100,101]}, index=pd.date_range('2026-01-01', periods=2))
hdf = pd.DataFrame([{'ticker':'CSPX.L','quantity':2}])
h, method = compute_market_value_from_holdings(hdf, prices, portfolio_value=1000)
assert h.loc[0,'market_value'] == 2*101 or method in ('shares_times_last_price','fallback_equal_due_to_missing_prices')



# Beispiel in einer REPL, Script oder Testsetup
low = ["AGGG.L", "EUNL.DE"]        # defensive / Low‑Risk ETFs
medium = ["IMEU.L", "SGLN.L"]     # mittleres Risiko
high = ["CSPX.L", "IQQ0.DE"]      # höheres Risiko / Aktien‑ETFs

rp_struct, rets, missing = build_regime_risk_parity_portfolio(low, medium, high, period="10y")
print("rp_struct keys:", rp_struct.keys())
print("missing tickers:", missing)

from risk_dashboard.core.investment_engine import build_regime_risk_parity_portfolio, backtest_regime_risk_parity
rp_struct, rets, missing = build_regime_risk_parity_portfolio(low, medium, high)
df, rp_struct, missing = backtest_regime_risk_parity(low_final, med_final, high_final, period="10y")
assert not df.empty
