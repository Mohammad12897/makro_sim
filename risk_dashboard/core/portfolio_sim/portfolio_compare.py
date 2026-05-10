#core/portfolio_sim/portfolio_compare.py
import pandas as pd

def run_portfolio_mc(*args, **kwargs):
    # Gibt Dummy-Werte zurÃ¼ck, damit nichts abstÃ¼rzt
    return None, None

def compare_portfolios(land, presets, portfolios, years, scenario):
    # Gibt eine leere Tabelle zurÃ¼ck, statt abzustÃ¼rzen
    df = pd.DataFrame(columns=[
        "Portfolio", "Mean", "VolatilitÃ¤t", "Sharpe", "VaR95", "CVaR95", "Max Drawdown"
    ])
    return df

