from tracemalloc import start

import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import numpy as np
import streamlit as st
import traceback
import logging
from typing import Optional
import inspect
import time
# falls normalize_price_df in derselben Datei definiert ist, kein Import nötig
# sonst z.B.:
from risk_dashboard.core.utils import get_latest_before, ensure_date_column, normalize_price_df


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


VALID_FALLBACKS = {
    "VEVE.L": "IMEU.L",
    "IGLT.L": "AGGG.L",
}

# Fallbacks für problematische EU-ETFs
ETF_FALLBACKS = {
    "VEVE.L": "IMEU.L",
    "IGLT.L": "AGGG.L",
    "SPY": "CSPX.L",
}

# -----------------------------------------------------
# 1) ETF-Daten herunterladen
# -----------------------------------------------------
import pandas as pd

def _to_naive_datetime_index(series: pd.Series) -> pd.Series:
    """
    Vereinheitlicht den Index einer Series:
    - stellt sicher, dass Index ein DatetimeIndex ist
    - konvertiert tz-aware Indizes nach UTC und entfernt tz-Info
    - falls nötig, rekonstruiert Index mit pd.to_datetime
    Rückgabe: Series mit tz-naive DatetimeIndex
    """
    # sicherstellen, dass Index DatetimeIndex ist
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")

    # falls tz-aware -> in UTC konvertieren und tz entfernen
    tz = getattr(series.index, "tz", None)
    if tz is not None:
        try:
            series.index = series.index.tz_convert("UTC").tz_localize(None)
        except Exception:
            # falls tz_convert fehlschlägt, versuche tz_localize(None)
            try:
                series.index = series.index.tz_localize(None)
            except Exception:
                # letzte Absicherung: rekonstruiere Index als naive Datetime
                series.index = pd.to_datetime(series.index.astype(str), errors="coerce")

    # drop NaT, falls Konvertierung fehlschlug
    series = series.dropna()
    return series


def _to_utc_aware_index(series: pd.Series) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    if getattr(series.index, "tz", None) is None:
        series.index = series.index.tz_localize("UTC")
    else:
        series.index = series.index.tz_convert("UTC")
    series = series.dropna()
    return series



def to_naive_utc(series: pd.Series) -> pd.Series:
    """
    Konvertiert eine Series so, dass ihr DatetimeIndex tz-naive ist.
    - Falls tz-aware: zuerst nach UTC konvertieren, dann tz entfernen.
    - Falls kein DatetimeIndex: pd.to_datetime verwenden.
    - Entfernt NaT nach Konvertierung.
    """
    # sicherstellen, dass Index ein DatetimeIndex ist
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")

    tz = getattr(series.index, "tz", None)
    if tz is not None:
        try:
            # erst nach UTC, dann tz entfernen
            series.index = series.index.tz_convert("UTC").tz_localize(None)
        except Exception:
            try:
                series.index = series.index.tz_localize(None)
            except Exception:
                series.index = pd.to_datetime(series.index.astype(str), errors="coerce")

    # drop NaT falls vorhanden
    series = series.dropna()
    return series

def to_utc_aware(series: pd.Series) -> pd.Series:
    """
    Alternative: macht Index tz-aware in UTC.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    if getattr(series.index, "tz", None) is None:
        series.index = series.index.tz_localize("UTC")
    else:
        series.index = series.index.tz_convert("UTC")
    return series.dropna()


# Helper 1: direkte yf.download
def _try_yf_download(ticker: str, start: Optional[str]=None, end: Optional[str]=None, period: Optional[str]=None) -> Optional[pd.Series]:
    try:
        if start is None and end is None:
            df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        else:
            df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if df is None or df.empty:
            logger.debug("yf.download returned empty for %s", ticker)
            return None
        if "Close" not in df.columns:
            logger.warning("yf.download for %s has no Close column: %s", ticker, df.columns.tolist())
            return None
        df.index = pd.to_datetime(df.index)
        s = df["Close"].copy()
        s.name = ticker
        return s.sort_index()
    except Exception:
        logger.exception("Error in _try_yf_download for %s", ticker)
        return None

# Helper 2: Ticker.history fallback
def _try_yf_ticker_history(ticker: str, start: Optional[str]=None, end: Optional[str]=None, period: Optional[str]=None) -> Optional[pd.Series]:
    try:
        t = yf.Ticker(ticker)
        if start is None and end is None:
            df = t.history(period=period, auto_adjust=True)
        else:
            df = t.history(start=start, end=end, auto_adjust=True)
        if df is None or df.empty:
            logger.debug("Ticker.history returned empty for %s", ticker)
            return None
        if "Close" not in df.columns:
            logger.warning("Ticker.history for %s has no Close column: %s", ticker, df.columns.tolist())
            return None
        df.index = pd.to_datetime(df.index)
        s = df["Close"].copy()
        s.name = ticker
        return s.sort_index()
    except Exception:
        logger.exception("Error in _try_yf_ticker_history for %s", ticker)
        return None

# Hauptfunktion: download_etf_history
def download_etf_history(tickers, start=None, end=None, period="10y", auto_resample=True, rate_limit_sleep: float = 0.2):
    if isinstance(tickers, str):
        tickers = [tickers]

    all_prices = {}
    debug_info = {}

    for t in tickers:
        debug_info[t] = {"attempts": []}

        # 1) Hauptversuch: yf.download
        s = _try_yf_download(t, start=start, end=end, period=period)
        debug_info[t]["attempts"].append(("download", s is not None and not getattr(s, "empty", False)))

        # 2) Fallback: Ticker.history helper
        if s is None or getattr(s, "empty", True):
            s = _try_yf_ticker_history(t, start=start, end=end, period=period)
            debug_info[t]["attempts"].append(("ticker_history", s is not None and not getattr(s, "empty", False)))

        # 3) Wenn immer noch leer → skip
        if s is None or getattr(s, "empty", True):
            st.warning(f"Keine Daten für {t} geladen.")
            debug_info[t]["result"] = "missing"
            debug_info[t]["raw_type"] = None if s is None else type(s).__name__
            continue

        # --- NEU: Normalisieren / Close-Extraktion ---
        # normalize_price_df behandelt MultiIndex und SingleIndex DataFrames
        if isinstance(s, pd.DataFrame):
            norm = normalize_price_df(s)
            if norm.empty:
                st.warning(f"{t}: DataFrame ohne 'Close'/'Adj Close' Spalte — wird übersprungen.")
                debug_info[t]["result"] = "missing_no_close"
                debug_info[t]["raw_type"] = "DataFrame_no_close"
                continue

            # norm kann mehrere Spalten enthalten (z.B. MultiTicker-Download)
            # Versuche, die Spalte für den aktuellen Ticker zu finden, sonst nimm erste Spalte
            if t in norm.columns:
                series = norm[t].copy()
            elif norm.shape[1] == 1:
                series = norm.iloc[:, 0].copy()
                series.name = t
            else:
                # heuristischer Fallback: erste Spalte
                series = norm.iloc[:, 0].copy()
                series.name = t
        else:
            # s ist bereits eine Series (z.B. Close Series)
            series = s.copy()
            series.name = t

        # Index und Sortierung sicherstellen
        series.index = pd.to_datetime(series.index, errors="coerce")
        series = series.sort_index()
        series = series.dropna()  # entferne NaNs in der Series

        if series.empty:
            st.warning(f"{t}: Nach Normalisierung keine gültigen Preise vorhanden.")
            debug_info[t]["result"] = "missing_after_norm"
            debug_info[t]["raw_type"] = type(s).__name__
            continue

        # Erfolgreich
        all_prices[t] = series
        debug_info[t]["result"] = "ok"
        debug_info[t]["first"] = str(series.index.min())
        debug_info[t]["last"] = str(series.index.max())

        # kleiner Sleep, um Rate Limits zu reduzieren
        time.sleep(rate_limit_sleep)

    # Debug-Ausgabe: vor DataFrame-Bau
    st.write("ETF-Loader Debug Info:", debug_info)
    st.write("DEBUG all_prices keys and types:")
    st.write({t: type(v).__name__ for t, v in all_prices.items()})
    for t, v in all_prices.items():
        try:
            shape = getattr(v, "shape", None)
            idx_preview = list(v.index[:3]) if hasattr(v, "index") else None
            st.write(t, "type:", type(v).__name__, "shape:", shape, "index_preview:", idx_preview)
        except Exception:
            st.write(t, "cannot inspect value")

    # Wenn ALLES leer → sauberes Verhalten
    if not all_prices:
        st.error("ETF-Loader: Keine Daten geladen.")
        return pd.DataFrame()

    # DataFrame bauen: nur gültige Series verwenden
    valid_items = {t: s for t, s in all_prices.items() if isinstance(s, pd.Series) and not s.empty}
    invalid = [t for t in all_prices.keys() if t not in valid_items]
    if invalid:
        st.warning(f"Die folgenden Ticker lieferten keine gültigen Series und werden übersprungen: {invalid}")
        st.write("Raw types:", {t: type(all_prices[t]).__name__ for t in invalid})

    if not valid_items:
        st.error("ETF-Loader: Keine gültigen Zeitreihen geladen.")
        return pd.DataFrame()

    # --- NEU: Vereinheitliche DatetimeIndex (tz-aware -> tz-naive UTC) vor concat ---
    def _to_naive_utc_index(series: pd.Series) -> pd.Series:
        # Sicherstellen, dass Index ein DatetimeIndex ist
        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.to_datetime(series.index, errors="coerce")
        # Falls tz-aware -> in UTC konvertieren und tz entfernen
        try:
            if getattr(series.index, "tz", None) is not None:
                series.index = series.index.tz_convert("UTC").tz_localize(None)
        except Exception:
            # Falls tz_convert fehlschlägt, versuche tz_localize(None) oder rekonstruiere Index
            try:
                series.index = series.index.tz_localize(None)
            except Exception:
                series.index = pd.to_datetime(series.index.astype(str), errors="coerce")
        return series

    normalized_series_list = []
    for t, s in valid_items.items():
        s_norm = _to_naive_utc_index(s.copy())
        # drop NaT nach Konvertierung
        s_norm = s_norm.dropna()
        if s_norm.empty:
            st.warning(f"{t}: Nach TZ-Normalisierung keine gültigen Zeitstempel mehr.")
            continue
        s_norm.name = t
        normalized_series_list.append(s_norm)

    if not normalized_series_list:
        st.error("ETF-Loader: Nach TZ-Normalisierung keine gültigen Zeitreihen.")
        return pd.DataFrame()



    # tz-naive Series
    idx_naive = pd.date_range("2020-01-01", periods=5, freq="D")
    s_naive = pd.Series(np.arange(5), index=idx_naive, name="NAIVE")

    # tz-aware Series (UTC)
    idx_aware = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    s_aware = pd.Series(np.arange(5)+10, index=idx_aware, name="AWARE")

    # Test helper
    s_aware_conv = to_naive_utc(s_aware)
    print("aware tz after conv:", getattr(s_aware_conv.index, "tz", None))
    print("naive tz:", getattr(s_naive.index, "tz", None))

    # concat should work now
    df = pd.concat([s_naive.rename("NAIVE"), s_aware_conv.rename("AWARE")], axis=1)
    print(df.head())



    prices = pd.concat(normalized_series_list, axis=1).sort_index()
    prices = prices.ffill().dropna(how="all")

    # Resample auf Monatsende falls gewünscht
    if auto_resample and not prices.empty:
        prices.index = pd.to_datetime(prices.index, errors="coerce")
        prices = prices.sort_index()
        prices = prices.resample("ME").last().ffill().dropna(how="all")

    return prices


# -----------------------------------------------------
# 2) Markt-Risikofaktoren erzeugen
# -----------------------------------------------------
def build_market_risk_factors(etf_prices: pd.DataFrame):
    """
    Erzeugt Momentum, Volatilität und Trend-Signale
    für den Markt (z. B. SPY).
    """

    df = pd.DataFrame(index=etf_prices.index)

    # Momentum (60 Tage)
    df["equity_momentum"] = etf_prices.pct_change(60).mean(axis=1)

    # Volatilität (20 Tage)
    df["equity_vol"] = etf_prices.pct_change().rolling(20).std().mean(axis=1)

    # Trend-Signal (Preis über gleitendem Durchschnitt?)
    ma = etf_prices.rolling(50).mean()
    df["equity_trend"] = (etf_prices > ma).mean(axis=1)

    return df.dropna()
