import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def ui_risk_dashboard(ticker_text):
    tickers = [t.strip() for t in ticker_text.split(",") if t.strip()]
    data = {}

    for t in tickers:
        series = fetch_price_history(t, period="1y")
        if isinstance(series, pd.Series):
            data[t] = series

    if not data:
        return pd.DataFrame([["Keine gültigen Daten"]]), pd.DataFrame(), None

    df = pd.DataFrame(data).dropna()
    returns = df.pct_change().dropna()

    vol_table = returns.std().reset_index()
    vol_table.columns = ["Ticker", "Volatilität"]

    dd_table = (df / df.cummax() - 1).min().reset_index()
    dd_table.columns = ["Ticker", "Max Drawdown"]

    fig = plot_correlation_heatmap(returns.corr())

    return vol_table, dd_table, fig
