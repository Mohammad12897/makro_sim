# risk_dashboard/core/analysis.py
import numpy as np
from typing import Tuple, Optional, List, Any, Union
import pandas as pd
import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Lokale Importe hier, um zirkuläre Abhängigkeiten zu vermeiden
from risk_dashboard.core.data_loader import (   
    load_raw_prices_for_universe,
    filter_valid_tickers
)
from risk_dashboard.core.ticker_cache import validate_ticker_with_cache
from risk_dashboard.data_cache import load_price_data_cached_with_used


@st.cache_data
def compute_metrics(close_series: pd.Series, trading_days: int = 252, rf: float = 0.0) -> dict:
    """Berechnet Risiko- und Performancekennzahlen für eine Preisserie."""
    close_series = pd.to_numeric(close_series, errors="coerce").dropna()
    if close_series.empty:
        raise ValueError("Close-Serie ist leer oder enthält keine numerischen Werte")

    rets = close_series.pct_change().dropna()
    ann_ret = (1 + rets.mean()) ** trading_days - 1
    ann_vol = rets.std() * (trading_days ** 0.5)
    sharpe = (ann_ret - rf) / ann_vol if ann_vol != 0 else float("nan")

    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    return {
        "annual_return": float(ann_ret),
        "annual_vol": float(ann_vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd)
    }

def _normalize_input_tickers(raw: str) -> List[str]:
    """
    Normalisiert Benutzereingaben:
    - entfernt äußere Anführungszeichen/ Klammern
    - ersetzt verschiedene Trenner durch Komma
    - split, trim, uppercase
    """
    if not raw:
        return []
    s = raw.strip()
    s = s.strip('"').strip("'").strip()
    for sep in [";", "|", "\n", "\t"]:
        s = s.replace(sep, ",")
    parts = [p.strip().strip('"').strip("'") for p in s.split(",")]
    return [p.upper() for p in parts if p]


def extract_close_series_for_used(prices_multi: pd.DataFrame, used: str) -> pd.Series:
    """
    Extrahiert die Close-Serie für 'used' aus prices_multi.
    Unterstützt MultiIndex-Index (mit '__ticker'), MultiIndex-Columns (ticker, OHLC)
    und flache Columns wie 'AAPL Close' oder 'Close'. Liefert eine rohe pd.Series.
    Raises KeyError wenn nichts gefunden wird.
    """
    if prices_multi is None:
        raise KeyError("prices_multi is None")
    used = str(used).strip()
    if not used:
        raise KeyError("Empty ticker 'used'")

    # 1) MultiIndex-Index (gestapelt)
    if isinstance(prices_multi.index, pd.MultiIndex):
        if "__ticker" in prices_multi.index.names:
            try:
                sub = prices_multi.xs(used, level="__ticker")
            except KeyError:
                raise KeyError(f"Ticker {used} nicht im MultiIndex-Level '__ticker'.")
            for col in ("Close", "Adj Close", "close", "adj close"):
                if col in sub.columns:
                    return sub[col]
            numeric_cols = sub.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                return sub[numeric_cols[0]]
            raise KeyError(f"Keine geeignete Close-Spalte für {used} im gestapelten DataFrame.")
        else:
            try:
                level0 = prices_multi.index.get_level_values(0)
            except Exception:
                raise KeyError("MultiIndex ohne zugängliche Level-Werte.")
            if used in level0:
                mask = level0 == used
                sub = prices_multi[mask]
                for col in ("Close", "Adj Close"):
                    if col in sub.columns:
                        return sub[col]
                numeric_cols = sub.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    return sub[numeric_cols[0]]
            raise KeyError(f"Ticker {used} nicht in MultiIndex-Index gefunden.")

    # 2) Columns sind MultiIndex (z.B. (ticker, 'Close'))
    if hasattr(prices_multi.columns, "nlevels") and prices_multi.columns.nlevels > 1:
        if (used, "Close") in prices_multi.columns:
            return prices_multi[(used, "Close")]
        if (used, "Adj Close") in prices_multi.columns:
            return prices_multi[(used, "Adj Close")]
        try:
            last_level = [str(x).lower() for x in prices_multi.columns.get_level_values(-1)]
            if any(x in ("close", "adj close", "adjclose", "adj") for x in last_level):
                if "Close" in prices_multi.columns.get_level_values(-1):
                    close_df = prices_multi.xs("Close", axis=1, level=-1, drop_level=True, errors="ignore")
                    if used in close_df.columns:
                        return close_df[used]
                if "Adj Close" in prices_multi.columns.get_level_values(-1):
                    adj_df = prices_multi.xs("Adj Close", axis=1, level=-1, drop_level=True, errors="ignore")
                    if used in adj_df.columns:
                        return adj_df[used]
        except Exception:
            pass
        for col in prices_multi.columns:
            if isinstance(col, tuple) and str(col[0]) == used:
                series = prices_multi[col]
                if pd.api.types.is_numeric_dtype(series):
                    return series
        raise KeyError(f"Keine Close-Spalte für {used} in MultiIndex-Columns gefunden.")

    # 3) Flache Columns (strings)
    cols = [str(c) for c in prices_multi.columns]
    for c in cols:
        lc = c.lower()
        if used.lower() in lc and "close" in lc:
            return prices_multi[c]
    if used in prices_multi.columns:
        return prices_multi[used]
    for c in ("Close", "Adj Close", "close", "adj close"):
        if c in prices_multi.columns:
            return prices_multi[c]
    numeric_cols = prices_multi.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        return prices_multi[numeric_cols[0]]

    raise KeyError(f"Keine geeignete Close-Spalte in DataFrame für ticker {used}.")


def analyze_ticker(base_ticker: str, etf_universe: List[str]) -> Tuple[
    Optional[str], Optional[pd.Series], Optional[dict], Optional[pd.DataFrame]
]:
    """
    Robust: akzeptiert 'AAPL' oder 'AAPL, CSPX.L' (Komma-getrennt).
    Validiert einzelne Ticker via validate_ticker_with_cache und verwendet
    den ersten gültigen Ticker (used). Gibt (used, close_series, metrics, prices_multi).
    """
    raw = (base_ticker or "").strip()
    if not raw:
        return None, None, None, None

    # Normalisieren und splitten
    candidates = _normalize_input_tickers(raw)
    candidates = [t for t in candidates if t]
    if not candidates:
        return None, None, None, None

    # Validierung
    valid_candidates = []
    invalid_candidates = []
    for t in candidates:
        try:
            if validate_ticker_with_cache(t):
                valid_candidates.append(t)
            else:
                invalid_candidates.append(t)
        except Exception:
            invalid_candidates.append(t)

    if invalid_candidates:
        logger.warning("Diese eingegebenen Ticker sind ungültig (Cache): %s", invalid_candidates)

    if not valid_candidates:
        logger.warning("Keine gültigen Ticker gefunden in Eingabe: %s", candidates)
        return None, None, None, None

    # Wähle ersten gültigen Ticker
    used = valid_candidates[0]

    # Lade ggf. gecachte Einzelpreise
    used_loaded, df = load_price_data_cached_with_used(used)
    if used_loaded is None or df is None or df.empty:
        logger.info("Ticker %s nicht gefunden oder keine Daten", used)
        return used, None, None, None

    # Universe erweitern und filtern
    custom_universe = list(dict.fromkeys([*(etf_universe or []), *valid_candidates]))
    custom_universe = [t.strip().upper() for t in custom_universe if isinstance(t, str) and t.strip()]
    custom_universe = list(dict.fromkeys(custom_universe))
    custom_universe = filter_valid_tickers(custom_universe)

    logger.info("Erweitertes, gefiltertes Universe: %s", custom_universe)

    try:
        prices_multi, skipped = load_raw_prices_for_universe(custom_universe)
    except Exception as e:
        logger.exception("Fehler beim Laden des erweiterten Universe für %s: %s", used, e)
        return used, None, None, None

    if skipped:
        logger.warning("Diese Ticker wurden entfernt, da sie keine Daten liefern: %s", skipped)

    # --- Extraktion der Rohserie (einmalig) ---
    logger.debug("prices_multi.columns: %s", list(prices_multi.columns)[:100])
    logger.debug("prices_multi.head: %s", prices_multi.head(10).to_dict())


    try:
        raw_series = extract_close_series_for_used(prices_multi, used)
    except KeyError as ke:
        logger.warning("Extraktion der Close-Serie fehlgeschlagen für %s: %s", used, ke)
        return used, None, None, prices_multi
    except Exception:
        logger.exception("Unexpected structure in prices_multi for %s", used)
        return used, None, None, prices_multi

    # --- Fallbacks und Konvertierung ---
    close_series = pd.Series(dtype="float64")

    # 1) Wenn Rohserie komplett NaN, versuche cached df als Fallback (lange Historie)
    try:
        if raw_series.isna().all():
            logger.info("raw_series for %s is all NaN — trying cached single-df fallback", used)
            if df is not None and not df.empty:
                # Priorität: typische Spalten
                for col in ("Close", "Adj Close", "close", "adj close"):
                    if col in df.columns:
                        candidate = pd.to_numeric(df[col], errors="coerce").dropna()
                        if not candidate.empty:
                            try:
                                candidate = candidate.reindex(prices_multi.index).dropna()
                            except Exception:
                                pass
                            close_series = candidate
                            logger.info("Using cached df column '%s' for %s as fallback", col, used)
                            break
                # fallback: erste numerische Spalte
                if close_series.empty:
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        candidate = pd.to_numeric(df[numeric_cols[0]], errors="coerce").dropna()
                        try:
                            candidate = candidate.reindex(prices_multi.index).dropna()
                        except Exception:
                            pass
                        if not candidate.empty:
                            close_series = candidate
                            logger.info("Using cached df numeric column '%s' for %s as fallback", numeric_cols[0], used)
    except Exception:
        logger.exception("Fehler beim Verwenden des cached df als Fallback für %s", used)

    # 2) Wenn noch leer: normale Konvertierung der Rohserie
    if close_series.empty:
        close_series = pd.to_numeric(raw_series, errors="coerce").dropna()

    # 3) Aggressive Fallbacks: MultiIndex-Columns oder flache Varianten durchsuchen
    if close_series.empty:
        try:
            if hasattr(prices_multi.columns, "nlevels") and prices_multi.columns.nlevels > 1:
                try:
                    close_df = prices_multi.xs("Close", axis=1, level=-1, drop_level=True, errors="ignore")
                    if used in close_df.columns:
                        candidate = pd.to_numeric(close_df[used], errors="coerce").dropna()
                        if not candidate.empty:
                            close_series = candidate
                            logger.info("Found Close via xs('Close') for %s", used)
                except Exception:
                    pass
                try:
                    adj_df = prices_multi.xs("Adj Close", axis=1, level=-1, drop_level=True, errors="ignore")
                    if used in adj_df.columns:
                        candidate = pd.to_numeric(adj_df[used], errors="coerce").dropna()
                        if not candidate.empty:
                            close_series = candidate
                            logger.info("Found Adj Close via xs('Adj Close') for %s", used)
                except Exception:
                    pass

            if close_series.empty:
                for c in prices_multi.columns:
                    cstr = str(c)
                    if used.lower() in cstr.lower() and "close" in cstr.lower():
                        candidate = pd.to_numeric(prices_multi[c], errors="coerce").dropna()
                        if not candidate.empty:
                            close_series = candidate
                            logger.info("Found numeric column '%s' for %s", cstr, used)
                            break
        except Exception:
            logger.exception("Aggressive column search failed for %s", used)

    # 4) Wenn weiterhin leer: Diagnose-Log und Rückgabe
    if close_series.empty:
        try:
            logger.debug("prices_multi.columns sample: %s", list(prices_multi.columns)[:50])
            logger.debug("prices_multi head (AAPL area): %s", prices_multi.head(10).to_dict())
            logger.debug("cached df head for %s: %s", used, None if df is None else df.head(10).to_dict())
        except Exception:
            logger.exception("Could not dump diagnostic samples for %s", used)

        logger.warning("Close-Serie für %s ist leer nach allen Konvertierungsversuchen", used)
        return used, None, None, prices_multi

    # Kennzahlen berechnen
    try:
        metrics = compute_metrics(close_series)
    except Exception as e:
        logger.exception("Fehler beim Berechnen der Kennzahlen für %s: %s", used, e)
        return used, close_series, None, prices_multi

    return used, close_series, metrics, prices_multi
