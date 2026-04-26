# risk_dashboard/core/fx_forecast.py
import pandas as pd
import yfinance as yf
from risk_dashboard.core.fx_engine import download_fx_history
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from risk_dashboard.core.utils import validate_prophet_input
from risk_dashboard.core.fx_engine import download_fx_history



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


def load_fx_history(pair="EURUSD=X", period="10y"):
    """
    Lädt historische FX-Daten von Yahoo Finance.
    Gibt DataFrame mit Spalten ['date', 'fx'] zurück.
    """
    data = yf.download(pair, period=period, interval="1d")

    if data.empty:
        raise ValueError(f"Keine FX-Daten für {pair} gefunden.")

    # MultiIndex-Spalten flach machen, falls nötig
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = ['_'.join([str(c) for c in col if c]) for col in data.columns]

    # FX-Spalte finden
    fx_col = None
    for col in data.columns:
        if "Close" in col or "fx" in col or pair in col:
            fx_col = col
            break

    if fx_col is None:
        raise ValueError(f"Keine FX-Spalte in Daten gefunden: {data.columns}")

    df = data[[fx_col]].rename(columns={fx_col: "fx"})
    df["date"] = df.index
    df = df[["date", "fx"]].dropna()

    return df


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


def forecast_fx_arima(steps=60, pair="EURUSD=X", period="10y", order=(1, 1, 1)):
    """
    ARIMA-basierte FX-Prognose.
    Rückgabe: (historie_df, forecast_df)
    """
    df = load_fx_history(pair=pair, period=period)
    s = df.set_index("date")["fx"].asfreq("D").ffill()

    model = ARIMA(s, order=order)
    res = model.fit()

    fc = res.get_forecast(steps=steps)
    fc_index = pd.date_range(start=s.index[-1] + pd.Timedelta(days=1), periods=steps, freq="D")
    fc_series = pd.Series(fc.predicted_mean.values, index=fc_index, name="fx")

    fc_df = fc_series.reset_index().rename(columns={"index": "date"})

    return df, fc_df


def forecast_fx(steps=30):
    df = load_fx_data()
    model = ARIMA(df["value"], order=(2,1,2))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=steps)
    return df, forecast


