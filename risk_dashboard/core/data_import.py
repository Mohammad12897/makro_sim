# core/data_import.py

import yfinance as yf
import pandas as pd
import numpy as np

def load_returns_csv(path: str, expected_assets: list = None) -> pd.DataFrame:
    """
    Lädt Rendite-CSV-Dateien (Equity, Bonds, Gold).
    - erkennt Datum automatisch
    - prüft Spalten
    - füllt fehlende Werte
    - sortiert nach Datum
    """

    df = pd.read_csv(path)

    # Datum erkennen
    if "date" not in df.columns:
        raise ValueError(f"CSV {path} muss eine 'date'-Spalte enthalten.")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    # Spalten prüfen
    if expected_assets:
        missing = set(expected_assets) - set(df.columns)
        if missing:
            raise ValueError(f"Fehlende Spalten in {path}: {missing}")

    # Fehlende Werte füllen
    df = df.fillna(method="ffill").fillna(method="bfill")

    # Sicherstellen, dass alles numerisch ist
    df = df.apply(pd.to_numeric, errors="coerce")

    return df

 
 def validate_returns(df, expected_assets):
    errors = []

    # Spalten prüfen
    for asset in expected_assets:
        if asset not in df.columns:
            errors.append(f"Fehlende Spalte: {asset}")

    # Datum prüfen
    if not isinstance(df.index, pd.DatetimeIndex):
        errors.append("Index ist kein Datum.")

    # Werte prüfen
    if df.isna().sum().sum() > 0:
        errors.append("Fehlende Werte in den Daten.")

    if (df > 1).any().any() or (df < -1).any().any():
        errors.append("Unrealistische Renditen (>100% oder < -100%).")

    return errors

def load_yahoo_returns(ticker, start="2010-01-01", end=None):
    data = yf.download(ticker, start=start, end=end)
    if "Adj Close" not in data:
        raise ValueError(f"Ticker {ticker} hat keine Adj Close Daten.")
    returns = data["Adj Close"].pct_change().dropna()
    return returns
