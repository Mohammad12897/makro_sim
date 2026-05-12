import yfinance as yf
import pandas as pd


def download_fx_history(tickers, period="10y"):
    data = yf.download(tickers, period=period)

    # Manche Indizes haben kein "Adj Close"
    if "Adj Close" in data.columns:
        data = data["Adj Close"]
    elif "Close" in data.columns:
        data = data["Close"]
    else:
        raise KeyError("Neither 'Adj Close' nor 'Close' found in downloaded FX data")

    # Falls Series → DataFrame
    if isinstance(data, pd.Series):
        data = data.to_frame()

    return data
