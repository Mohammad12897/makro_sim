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
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
from datetime import datetime, timedelta
# falls normalize_price_df in derselben Datei definiert ist, kein Import nÃ¶tig
# sonst z.B.:
from risk_dashboard.core.utils import get_latest_before, ensure_date_column, ensure_date_series, normalize_price_df


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


VALID_FALLBACKS = {
    "VEVE.L": "IMEU.L",
    "IGLT.L": "AGGG.L",
}

# Fallbacks fÃ¼r problematische EU-ETFs
ETF_FALLBACKS = {
    "VEVE.L": "IMEU.L",
    "IGLT.L": "AGGG.L",
    "SPY": "CSPX.L",
}

# -----------------------------------------------------
# 1) ETF-Daten herunterladen
# -----------------------------------------------------



def _safe_linkage_from_dist(dist, method="single"):
    arr = np.asarray(dist)
    if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
        condensed = squareform(arr)
        return linkage(condensed, method=method)
    else:
        return linkage(arr, method=method)

# Verwendung:
# Z = _safe_linkage_from_dist(dist, method="single")
# order = leaves_list(Z)


# --- ErgÃ¤nzungen in risk_dashboard/core/market_engine.py ---



def ensure_datetime_index(df: pd.DataFrame, date_col: str = None) -> pd.DataFrame:
    """
    Stellt sicher, dass DataFrame einen DatetimeIndex hat.
    - date_col: falls angegeben, wird diese Spalte in den Index konvertiert.
    """
    if date_col:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    else:
        # falls Index bereits datetime-like
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass
    return df

def force_tz_aware(df: pd.DataFrame, tz: str = "UTC") -> pd.DataFrame:
    """
    Macht Index timezone-aware (falls noch naive) mit tz (z.B. 'UTC' oder 'Europe/Berlin').
    """
    idx = pd.to_datetime(df.index)
    if idx.tz is None:
        df.index = idx.tz_localize(tz)
    else:
        df.index = idx.tz_convert(tz)
    return df

def force_tz_naive(df: pd.DataFrame) -> pd.DataFrame:
    """
    Entfernt tz-Informationen vom Index (macht naive).
    """
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        df.index = idx.tz_convert("UTC").tz_localize(None)
    else:
        df.index = idx
    return df

# Beispielanwendung beim Laden:
# df = load_price_data(...)
# df = ensure_datetime_index(df, date_col="date")
# df = force_tz_naive(df)  # oder force_tz_aware(df, tz="UTC")


def _to_naive_datetime_index(series: pd.Series) -> pd.Series:
    """
    Vereinheitlicht den Index einer Series:
    - stellt sicher, dass Index ein DatetimeIndex ist
    - konvertiert tz-aware Indizes nach UTC und entfernt tz-Info
    - falls nÃ¶tig, rekonstruiert Index mit pd.to_datetime
    RÃ¼ckgabe: Series mit tz-naive DatetimeIndex
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
            # falls tz_convert fehlschlÃ¤gt, versuche tz_localize(None)
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

        # Index sicherstellen
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            df = ensure_date_column(df, date_col="date")
            df = df.set_index("date")

        # Preisspalte finden (Adj Close bevorzugt)
        price_col = None
        for candidate in ["Adj Close", "Close", "adj_close", "close"]:
            if candidate in df.columns:
                price_col = candidate
                break

        if price_col is None:
            logger.warning("yf.download for %s has no Close/Adj Close column: %s", ticker, df.columns.tolist())
            return None

        # Normalisieren (Index, Duplikate, Sortierung) â€” normalize_price_df erwartet price_col
        df = normalize_price_df(df, price_col=price_col)

        # Extrahiere die Preisâ€‘Series (erste Spalte nach normalize_price_df)
        s = df.iloc[:, 0].copy()
        s.name = ticker
        return s.sort_index()

    except Exception:
        logger.exception("Error in _try_yf_download for %s", ticker)
        return None



def _try_yf_ticker_history(ticker: str, start: Optional[str]=None, end: Optional[str]=None, period: Optional[str]=None) -> Optional[pd.Series]:
    """
    Fallback: Verwende yfinance.Ticker(ticker).history(...) falls yf.download fehlschlÃ¤gt.
    Liefert eine Series (Close/Adj Close) oder None.
    """
    try:
        tk = yf.Ticker(ticker)
        if start is None and end is None:
            df = tk.history(period=period, auto_adjust=True)
        else:
            df = tk.history(start=start, end=end, auto_adjust=True)
        if df is None or df.empty:
            return None

        # Index sicherstellen
        df.index = pd.to_datetime(df.index)

        # Bevorzugt "Close" oder "Adj Close"
        for candidate in ["Adj Close", "Close", "adj_close", "close"]:
            if candidate in df.columns:
                series = df[candidate].copy()
                series.name = ticker
                return series.sort_index()

        return None
    except Exception:
        logger.exception("Error in _try_yf_ticker_history for %s", ticker)
        return None

def download_etf_history(tickers, start=None, end=None, period="10y", auto_resample=True, rate_limit_sleep: float = 0.2):
    if isinstance(tickers, str):
        tickers = [tickers]

    all_prices = {}
    debug_info = {}

    for t in tickers:
        debug_info[t] = {"attempts": []}

        s = _try_yf_download(t, start=start, end=end, period=period)
        debug_info[t]["attempts"].append(("download", s is not None and not getattr(s, "empty", False)))

        # optionaler Fallback: nur wenn Funktion vorhanden
        if (s is None or getattr(s, "empty", True)) and "_try_yf_ticker_history" in globals():
            s = _try_yf_ticker_history(t, start=start, end=end, period=period)
            debug_info[t]["attempts"].append(("ticker_history", s is not None and not getattr(s, "empty", False)))

        if s is None or getattr(s, "empty", True):
            st.warning(f"Keine Daten fÃ¼r {t} geladen.")
            debug_info[t]["result"] = "missing"
            debug_info[t]["raw_type"] = None if s is None else type(s).__name__
            continue

        # Falls DataFrame -> normalize und Series extrahieren
        if isinstance(s, pd.DataFrame):
            try:
                # zuerst sicherstellen, dass eine Datumsspalte/Index vorhanden ist
                s = ensure_date_column(s, date_col="date") if "date" in s.columns else s
                # normalize_price_df erwartet price_col; wenn nicht Ã¼bergeben, versucht sie, eine Preisspalte zu finden
                norm = normalize_price_df(s)
            except Exception:
                st.warning(f"{t}: DataFrame konnte nicht normalisiert werden â€” wird Ã¼bersprungen.")
                debug_info[t]["result"] = "missing_no_close"
                debug_info[t]["raw_type"] = "DataFrame_no_close"
                continue

            # WÃ¤hle Series aus norm
            if t in norm.columns:
                series = norm[t].copy()
            elif norm.shape[1] >= 1:
                series = norm.iloc[:, 0].copy()
                series.name = t
            else:
                st.warning(f"{t}: Normalisierte DataFrame enthÃ¤lt keine Spalten.")
                debug_info[t]["result"] = "missing_no_close"
                debug_info[t]["raw_type"] = "DataFrame_no_close"
                continue
        else:
            # s ist Series
            series = s.copy()
            series.name = t

        # Index und Sortierung sicherstellen
        series.index = pd.to_datetime(series.index, errors="coerce")
        series = series.sort_index().dropna()

        if series.empty:
            st.warning(f"{t}: Nach Normalisierung keine gÃ¼ltigen Preise vorhanden.")
            debug_info[t]["result"] = "missing_after_norm"
            debug_info[t]["raw_type"] = type(s).__name__
            continue

        all_prices[t] = series
        debug_info[t]["result"] = "ok"
        debug_info[t]["first"] = str(series.index.min())
        debug_info[t]["last"] = str(series.index.max())

        time.sleep(rate_limit_sleep)

    # Debug-Ausgabe
    st.write("ETF-Loader Debug Info:", debug_info)
    st.write("DEBUG all_prices keys and types:")
    st.write({t: type(v).__name__ for t, v in all_prices.items()})

    if not all_prices:
        st.error("ETF-Loader: Keine Daten geladen.")
        return pd.DataFrame()

    valid_items = {t: s for t, s in all_prices.items() if isinstance(s, pd.Series) and not s.empty}
    invalid = [t for t in all_prices.keys() if t not in valid_items]
    if invalid:
        st.warning(f"Die folgenden Ticker lieferten keine gÃ¼ltigen Series und werden Ã¼bersprungen: {invalid}")
        st.write("Raw types:", {t: type(all_prices[t]).__name__ for t in invalid})

    if not valid_items:
        st.error("ETF-Loader: Keine gÃ¼ltigen Zeitreihen geladen.")
        return pd.DataFrame()

    df = pd.DataFrame(valid_items)
    return df

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
            # Falls tz_convert fehlschlÃ¤gt, versuche tz_localize(None) oder rekonstruiere Index
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
            st.warning(f"{t}: Nach TZ-Normalisierung keine gÃ¼ltigen Zeitstempel mehr.")
            continue
        s_norm.name = t
        normalized_series_list.append(s_norm)

    if not normalized_series_list:
        st.error("ETF-Loader: Nach TZ-Normalisierung keine gÃ¼ltigen Zeitreihen.")
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

    # Resample auf Monatsende falls gewÃ¼nscht
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
    Erzeugt Momentum, VolatilitÃ¤t und Trend-Signale
    fÃ¼r den Markt (z. B. SPY).
    """

    df = pd.DataFrame(index=etf_prices.index)

    # Momentum (60 Tage)
    df["equity_momentum"] = etf_prices.pct_change(60).mean(axis=1)

    # VolatilitÃ¤t (20 Tage)
    df["equity_vol"] = etf_prices.pct_change().rolling(20).std().mean(axis=1)

    # Trend-Signal (Preis Ã¼ber gleitendem Durchschnitt?)
    ma = etf_prices.rolling(50).mean()
    df["equity_trend"] = (etf_prices > ma).mean(axis=1)

    return df.dropna()

