import yfinance as yf
import pandas as pd
import logging

from typing import Sequence, Tuple, Optional

logger = logging.getLogger(__name__)


def _flatten_yf_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Robust flatten yfinance output:
    - Wenn MultiIndex: versuche zuerst (ticker, field) -> wähle 'Close' pro Ticker.
    - Falls (field, ticker): wähle 'Close' Ebene.
    - Falls keine 'Close' Ebene vorhanden ist, wähle die erste numerische Spalte pro Ticker.
    - Liefert DataFrame mit eindeutigen Spaltennamen (Ticker).
    """
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    # MultiIndex-Fall
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = df.columns.get_level_values(0)
        lvl1 = df.columns.get_level_values(1)

        # Fall: (ticker, field) z.B. ('VOO','Close')
        # Heuristik: viele lvl0 Einträge sind Ticker (alphanumerisch)
        try:
            # Suche Close in Ebene 1 (case-insensitive)
            close_label = None
            for lab in df.columns.levels[1]:
                if str(lab).lower() == "close":
                    close_label = lab
                    break
            if close_label is not None:
                out = df.xs(close_label, axis=1, level=1)
                out.columns = [str(c).upper() for c in out.columns]
                return out
        except Exception:
            pass

        # Fall: (field, ticker) z.B. ('Close','VOO')
        try:
            close_label = None
            for lab in df.columns.levels[0]:
                if str(lab).lower() == "close":
                    close_label = lab
                    break
            if close_label is not None:
                out = df.xs(close_label, axis=1, level=0)
                out.columns = [str(c).upper() for c in out.columns]
                return out
        except Exception:
            pass

        # Fallback: für jeden Ticker die erste numerische Spalte nehmen
        cols = {}
        # bestimme mögliche ticker-level (beide Ebenen prüfen)
        for lvl in (0, 1):
            try:
                for t in sorted(set(df.columns.get_level_values(lvl))):
                    sub = df[t] if t in df.columns else None
                    if sub is None:
                        # try selecting by tuple
                        try:
                            sub = df.xs(t, axis=1, level=lvl)
                        except Exception:
                            sub = None
                    if sub is not None:
                        num = sub.select_dtypes("number")
                        if not num.empty:
                            cols[str(t).upper()] = num.iloc[:, 0]
                if cols:
                    return pd.DataFrame(cols)
            except Exception:
                continue

        # Letzter Fallback: concat aller Spalten mit eindeutigen Namen TICKER_FIELD
        try:
            pieces = []
            names = []
            for f, t in df.columns:
                pieces.append(df[(f, t)])
                names.append(f"{str(t).upper()}_{str(f).upper()}")
            return pd.concat(pieces, axis=1).set_axis(names, axis=1)
        except Exception:
            pass

    # Kein MultiIndex: sichere Umbenennung bei Duplikaten
    cols = list(df.columns)
    seen = {}
    new_cols = []
    for c in cols:
        key = str(c).upper()
        if key in seen:
            seen[key] += 1
            new_cols.append(f"{key}_{seen[key]}")
        else:
            seen[key] = 0
            new_cols.append(key)
    df.columns = new_cols
    return df


def fetch_prices_quiet(tickers, start="2010-01-01", end=None):
    """
    Lädt Preisdaten für eine Liste von Tickers.
    Gibt IMMER NUR ein DataFrame zurück (kein used, df).
    MultiIndex wird automatisch bereinigt.
    """

    if isinstance(tickers, str):
        tickers = [tickers]

    logger.debug("fetch_prices_quiet start tickers=%s start=%s end=%s", tickers, start, end)

    try:
        df = yf.download(
            tickers,
            start=start,
            end=end,
            progress=False,
            group_by="ticker",
            auto_adjust=False,
            threads=True
        )
    except Exception as e:
        logger.warning("fetch_prices_quiet failed for %s: %s", tickers, e)
        return pd.DataFrame()

    if df is None or df.empty:
        logger.warning("fetch_prices_quiet returned empty DataFrame for %s", tickers)
        return pd.DataFrame()

    # MultiIndex flatten
    if isinstance(df.columns, pd.MultiIndex):
        logger.debug("DataFrame is MultiIndex with levels %s", df.columns.nlevels)
        try:
            # Falls Ebene "Close" existiert → nur Close nehmen
            if "Close" in df.columns.get_level_values(0):
                df = df.xs("Close", axis=1, level=0, drop_level=False)
            else:
                # sonst letzte Ebene (Ticker)
                df.columns = df.columns.get_level_values(-1)
        except Exception as e:
            logger.warning("MultiIndex flatten failed: %s", e)
            df.columns = df.columns.get_level_values(-1)

    # Index bereinigen
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    logger.debug(
        "fetch_prices_quiet returning dataframe with columns %s and index %s",
        list(df.columns),
        df.index[:3] if len(df.index) > 3 else df.index
    )

    return df


def extract_close_series(df, ticker):
    """
    Extrahiert die Close-Serie eines einzelnen Tickers aus einem DataFrame.
    Robust gegen MultiIndex, verschiedene Spaltennamen und fehlende Daten.
    """

    if df is None or df.empty:
        return pd.Series(dtype=float)

    # MultiIndex flatten falls nötig
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if "Close" in df.columns.get_level_values(0):
                df = df.xs("Close", axis=1, level=0, drop_level=False)
            else:
                df.columns = df.columns.get_level_values(-1)
        except Exception:
            df.columns = df.columns.get_level_values(-1)

    # mögliche Spaltennamen
    candidates = [
        ticker,
        ticker.upper(),
        ticker.lower(),
        "Close",
        "close",
        "Adj Close",
        "adjclose"
    ]

    for col in candidates:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                return s

    # fallback: erste numerische Spalte
    numeric_cols = df.select_dtypes("number").columns.tolist()
    if numeric_cols:
        return df[numeric_cols[0]].dropna()

    return pd.Series(dtype=float)


def _normalize_tickers(tickers: Sequence[str]) -> list:
    return [t.strip() for t in tickers if t and str(t).strip()]

def fetch_prices_quiet_with_used(tickers: Sequence[str] | str,
                                 start: str = "2010-01-01",
                                 end: Optional[str] = None) -> Tuple[Optional[str], pd.DataFrame]:
    if isinstance(tickers, str):
        tickers = [tickers]
    tickers = _normalize_tickers(tickers)
    if not tickers:
        return None, pd.DataFrame()

    logger.debug("fetch_prices_quiet_with_used start tickers=%s start=%s end=%s", tickers, start, end)

    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            progress=False,
            group_by="ticker",
            auto_adjust=False,
            threads=True
        )
    except Exception as e:
        logger.warning("yfinance download failed for %s: %s", tickers, e)
        return None, pd.DataFrame()

    if raw is None or raw.empty:
        logger.warning("fetch_prices_quiet_with_used returned empty for %s", tickers)
        return None, pd.DataFrame()

    # Robustes Flattening
    df = _flatten_yf_dataframe(raw)

    # Spalten auf Großbuchstaben (einheitlich)
    df.columns = [str(c).upper() for c in df.columns]

    # Bestimme 'used' als erster Ticker, der tatsächlich Spalte liefert
    used = None
    for t in tickers:
        if str(t).upper() in df.columns:
            used = t
            break
    if used is None:
        numeric_cols = df.select_dtypes("number").columns.tolist()
        used = numeric_cols[0] if numeric_cols else None

    # Index in Datetime konvertieren
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    logger.debug("fetch_prices_quiet_with_used returning used=%s df.shape=%s", used, df.shape)
    return used, df
