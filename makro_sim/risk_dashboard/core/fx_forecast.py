# risk_dashboard/core/fx_forecast.py
import logging
from typing import Tuple
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_datareader.data as pdr
from risk_dashboard.core.fx_engine import download_fx_history
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from risk_dashboard.core.utils import validate_prophet_input
from risk_dashboard.core.fx_engine import download_fx_history


logger = logging.getLogger(__name__)

import logging
from typing import Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

def _ensure_date_fx_columns(df: pd.DataFrame, fx_col_name: str) -> pd.DataFrame:
    """
    Hilfsfunktion: nimmt ein DataFrame mit einem Preiskolumnennamen fx_col_name
    und stellt sicher, dass die Spalten 'date' und 'fx' existieren.
    """
    # reset_index und sichere Umbenennung der Index-Spalte in 'date'
    out = df.reset_index()
    # Falls die Index-Spalte bereits 'date' heißt, ist das fine.
    if "date" not in out.columns:
        # Die erste Spalte nach reset_index ist die ehemalige Index-Spalte
        idx_col = out.columns[0]
        out = out.rename(columns={idx_col: "date"})
    # Falls fx_col_name nicht exakt vorhanden ist (z. B. durch Umbenennung), versuche Fallback
    if fx_col_name not in out.columns:
        # Suche erste numerische Spalte (außer 'date')
        numeric = [c for c in out.select_dtypes(include="number").columns if c != "date"]
        if numeric:
            fx_col_name = numeric[0]
        else:
            # kein numerisches Feld gefunden -> leeres DF
            return pd.DataFrame(columns=["date", "fx"])
    # Jetzt sicherstellen, dass 'fx' existiert
    out = out.rename(columns={fx_col_name: "fx"})
    # Konvertiere Datumsspalte
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "fx"])
    out = out[["date", "fx"]].copy()
    return out

def load_fx_history(pair: str = "EURUSD=X", period: str = "10y") -> pd.DataFrame:
    """
    Lade FX-Historie für ein Währungspaar.
    Rückgabe: DataFrame mit Spalten ['date','fx'] oder ein leeres DataFrame mit diesen Spalten.
    """
    # 1) Versuch: yfinance
    try:
        data = yf.download(pair, period=period, interval="1d", progress=False)
    except Exception as e:
        logger.warning("yf.download error for %s: %s", pair, e)
        data = pd.DataFrame()

    # 2) Wenn yfinance leer oder None -> Fallback versuchen
    if data is None or data.empty:
        logger.info("yf.download returned empty for %s, trying fallback sources...", pair)
        try:
            import pandas_datareader.data as pdr  # type: ignore
            symbol = pair.replace("=X", "")
            df_alt = pdr.DataReader(symbol, "stooq")
            if df_alt is None or df_alt.empty:
                logger.info("pandas_datareader (stooq) returned no data for %s", pair)
                return pd.DataFrame(columns=["date", "fx"])
            df_alt.index = pd.to_datetime(df_alt.index, errors="coerce")
            df_alt = df_alt.sort_index()
            # Wähle die letzte numerische Spalte als FX-Preis
            numeric_cols = df_alt.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                logger.info("Fallback data for %s has no numeric columns", pair)
                return pd.DataFrame(columns=["date", "fx"])
            out = df_alt[[numeric_cols[-1]]].copy()
            return _ensure_date_fx_columns(out, numeric_cols[-1])
        except Exception as e:
            logger.info("Fallback sources failed for %s: %s", pair, e)
            return pd.DataFrame(columns=["date", "fx"])

    # 3) Wenn yfinance Daten liefert: Normalisieren und Spalte auswählen
    try:
        # Falls MultiIndex-Spalten vorhanden sind, flach machen
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [" ".join(map(str, c)).strip() for c in data.columns.values]

        data.index = pd.to_datetime(data.index, errors="coerce")
        # Bevorzugte Spaltenreihenfolge
        for candidate in ["Adj Close", "Close", "adj_close", "close"]:
            if candidate in data.columns:
                out = data[[candidate]].copy()
                return _ensure_date_fx_columns(out, candidate)

        # Fallback: erste numerische Spalte
        numeric_cols = data.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            out = data[[numeric_cols[0]]].copy()
            return _ensure_date_fx_columns(out, numeric_cols[0])

        # Keine passende Spalte gefunden
        logger.warning("No suitable price column found for %s (columns: %s)", pair, data.columns.tolist())
        return pd.DataFrame(columns=["date", "fx"])

    except Exception as e:
        logger.exception("Error processing yfinance data for %s: %s", pair, e)
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


