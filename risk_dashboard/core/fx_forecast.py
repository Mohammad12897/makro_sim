# risk_dashboard/core/fx_forecast.py
import logging
from typing import Tuple, Optional, List
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_datareader.data as pdr
from risk_dashboard.core.fx_engine import download_fx_history
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from risk_dashboard.core.utils import validate_prophet_input
from risk_dashboard.core.fx_engine import download_fx_history
import requests
from risk_dashboard.core.yf_helper import _safe_read_csv_text

import logging


from risk_dashboard.data_utils import flatten_yf_dataframe, fetch_prices_from_yf

logger = logging.getLogger(__name__)

def _try_import_pandas_datareader():
    try:
        import importlib
        spec = importlib.util.find_spec("pandas_datareader")
        if spec is None:
            return None
        import pandas_datareader.data as pdr  # type: ignore
        return pdr
    except Exception as e:
        logger.info("pandas_datareader import failed: %s", e)
        return None


def load_fx_history(pair: str = "EURUSD=X", period: str = "10y") -> pd.DataFrame:
    """
    Lade FX-Historie für ein Währungspaar.
    Rückgabe: DataFrame mit Spalte ['fx'] und DatetimeIndex.
    """
    # 1) Versuche zentrale Funktion
    try:
        df = fetch_prices_from_yf(pair, start=None, end=None, interval="1d")
    except Exception as e:
        logger.warning("fetch_prices_from_yf error for %s: %s", pair, e)
        df = pd.DataFrame()

    # 2) Fallbacks falls leer
    if df is None or df.empty:
        logger.info("fetch_prices_from_yf returned empty for %s, trying fallbacks...", pair)
        # (Behalte hier deine bestehenden pandas_datareader / HTTP CSV Fallbacks unverändert)
        # ... (kopiere den bisherigen Fallback‑Block aus deiner Datei)
        # Wenn alle Fallbacks fehlschlagen:
        return pd.DataFrame(columns=["date", "fx"])

    # 3) Normalisieren
    try:
        if isinstance(df.columns, pd.MultiIndex):
            df = flatten_yf_dataframe(df)

        df.index = pd.to_datetime(df.index, errors="coerce")
        # Bevorzugte Spaltenreihenfolge
        for candidate in ["Adj Close", "AdjClose", "Adj_Close", "Close", "close"]:
            # flexible Suche (case-insensitive)
            match = [c for c in df.columns if c.upper().replace("_"," ") == candidate.upper().replace("_"," ")]
            if match:
                out = df[[match[0]]].copy()
                out.columns = ["fx"]
                out = out.sort_index()
                out.index.name = "date"
                return out

        # Fallback: erste numerische Spalte
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            out = df[[numeric_cols[0]]].copy()
            out.columns = ["fx"]
            out.index.name = "date"
            return out

        logger.warning("No suitable price column found for %s (columns: %s)", pair, df.columns.tolist())
        return pd.DataFrame(columns=["date", "fx"])

    except Exception as e:
        logger.exception("Error processing data for %s: %s", pair, e)
        return pd.DataFrame(columns=["date", "fx"])


def load_fx_data():
    """
    Lädt FX-Daten für Forecasting (z. B. DEXUSEU = USD/EUR).
    """
    df = download_fx_history(["DEXUSEU"], period="10y")

    df = df.rename(columns={"DEXUSEU": "y"})
    df = df.reset_index().rename(columns={"Date": "ds"})

    # ARIMA braucht tägliche Frequenz
    df = df.set_index("ds").asfreq("D").interpolate()

    return df.reset_index()


def forecast_fx_prophet(steps=60, pair="EURUSD=X", period="10y"):
    """
    Prophet-basierte FX-Prognose.
    Rückgabe: (historie_df, forecast_df)
    """
    df = load_fx_history(pair=pair, period=period)

    # Prophet-Format
    df = df.rename(columns={"date": "ds", "fx": "y"})
    df["ds"] = pd.to_datetime(df["ds"])

    df = validate_prophet_input(df)

    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=steps, freq="D")
    forecast = model.predict(future)

    return df, forecast

def forecast_fx_arima(pair: str = "EURUSD=X",
                      period: str = "10y",
                      steps: int = 60,
                      order: tuple = (1, 1, 1)
                      ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    ARIMA-basierte FX-Prognose.
    Rückgabe: (historie_df, forecast_df)
    - historie_df: DataFrame mit Spalten ['date','fx'] (historische Werte) oder leeres DF
    - forecast_df: DataFrame mit Spalten ['date','fx_forecast'] (Vorhersage für 'steps' Tage) oder leeres DF

    Die Funktion ist fehlertolerant:
    - Wenn keine Daten vorhanden sind, werden leere DataFrames zurückgegeben.
    - Wenn die Modellanpassung fehlschlägt, wird ebenfalls ein leeres Forecast-DF zurückgegeben.
    """
    try:
        # Lade Daten (load_fx_history muss ein DF mit 'date' und 'fx' liefern oder ein leeres DF)
        df = load_fx_history(pair=pair, period=period)
    except Exception as e:
        logger.exception("Fehler beim Laden der FX-Historie für %s: %s", pair, e)
        return pd.DataFrame(columns=["date", "fx"]), pd.DataFrame(columns=["date", "fx_forecast"])

    # Prüfen, ob Daten vorhanden und korrekt formatiert sind
    if df is None or df.empty:
        logger.warning("Skipping FX forecast: no data for %s", pair)
        return pd.DataFrame(columns=["date", "fx"]), pd.DataFrame(columns=["date", "fx_forecast"])

    # Sicherstellen, dass 'date' und 'fx' vorhanden sind
    if "date" not in df.columns or "fx" not in df.columns:
        logger.warning("FX data for %s missing required columns: %s", pair, df.columns.tolist())
        return pd.DataFrame(columns=["date", "fx"]), pd.DataFrame(columns=["date", "fx_forecast"])

    # Konvertiere Datum und sortiere
    try:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "fx"])
        df = df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        logger.exception("Fehler bei der Datumskonvertierung für %s: %s", pair, e)
        return pd.DataFrame(columns=["date", "fx"]), pd.DataFrame(columns=["date", "fx_forecast"])

    if df.empty:
        logger.warning("After cleaning, no FX data left for %s", pair)
        return pd.DataFrame(columns=["date", "fx"]), pd.DataFrame(columns=["date", "fx_forecast"])

    # Erzeuge Zeitreihe mit täglicher Frequenz und fülle fehlende Werte vorwärts
    try:
        ts = df.set_index("date")["fx"].asfreq("D").ffill()
        # Falls noch NaNs am Anfang existieren, entferne sie
        ts = ts.dropna()
        if ts.empty:
            logger.warning("Time series for %s is empty after resampling/ffill.", pair)
            return df[["date", "fx"]], pd.DataFrame(columns=["date", "fx_forecast"])
    except KeyError as e:
        logger.warning("Missing expected column when building time series for %s: %s", pair, e)
        return df[["date", "fx"]], pd.DataFrame(columns=["date", "fx_forecast"])
    except Exception as e:
        logger.exception("Error preparing time series for %s: %s", pair, e)
        return df[["date", "fx"]], pd.DataFrame(columns=["date", "fx_forecast"])

    # ARIMA-Modell anpassen und vorhersagen
    try:
        model = ARIMA(ts, order=order)
        res = model.fit()
        # Forecast für 'steps' Tage
        fc = res.get_forecast(steps=steps)
        fc_index = pd.date_range(start=ts.index[-1] + pd.Timedelta(days=1), periods=steps, freq="D")
        fc_mean = fc.predicted_mean
        # Falls fc_mean Index nicht daily ist, setze unseren Index
        if not isinstance(fc_mean.index, pd.DatetimeIndex):
            fc_mean.index = fc_index[:len(fc_mean)]
        forecast_df = pd.DataFrame({"date": fc_mean.index, "fx_forecast": fc_mean.values})
        # Historische DF zurückgeben (bereinigt)
        hist_df = df[["date", "fx"]].copy()
        return hist_df, forecast_df
    except Exception as e:
        logger.exception("ARIMA modelling/forecast failed for %s: %s", pair, e)
        return df[["date", "fx"]], pd.DataFrame(columns=["date", "fx_forecast"])


def forecast_fx(steps=30):
    df = load_fx_data()
    model = ARIMA(df["value"], order=(2,1,2))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=steps)
    return df, forecast