# scripts/test_csv.py
# python scripts/test_csv.py
import os
import time
import datetime
import random
from pathlib import Path
import logging
import pandas as pd
import requests
from urllib.parse import quote


# lokale Hilfsfunktionen aus deinem Projekt
from yf_helper import _safe_read_csv_text, wait_for_rate_slot, _ensure_date_fx_columns  # _ensure_date_fx_columns ggf. anpassen

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)



def try_http_fallbacks(pair, start_ts, end_ts):
    symbol_stooq = pair.replace("=X","").lower()
    symbol_yahoo = pair  # keep Yahoo ticker format (e.g., "EURUSD=X")

    stooq_url = f"https://stooq.com/q/d/l/?s={symbol_stooq}&i=d"
    yahoo_url = ("https://query1.finance.yahoo.com/v7/finance/download/"
                 f"{quote(symbol_yahoo)}?period1={start_ts}&period2={end_ts}&interval=1d&events=history&includeAdjustedClose=true")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    urls = [stooq_url, yahoo_url]

    for url in urls:
        try:
            wait_for_rate_slot()
            r = requests.get(url, timeout=15, headers=headers)
            r.raise_for_status()
            
            # Debug: Status, Content-Type und sichere Vorschau (keine echten Zeilenumbrüche)
            logger.debug("Fallback response %s %s %s", url, r.status_code, r.headers.get("content-type"))
            preview = r.text[:1000].replace("\n", "\\n")
            logger.debug("Preview: %s", preview)
        except requests.RequestException as e:
            logger.debug("HTTP request failed for %s: %s", url, e)
            continue

        ct = r.headers.get("content-type","").lower()
        if "text/csv" not in ct and "<html" in r.text.lower():
            logger.warning("Fallback returned HTML or non-CSV for %s", url)
            logger.debug("Response preview: %s", r.text[:1000])
            continue

        try:
            df = _safe_read_csv_text(r.text)
        except ValueError:
            logger.warning("Fallback returned invalid CSV/HTML for %s", url)
            logger.debug("Response preview: %s", r.text[:1000])
            continue

        if df is None or df.empty:
            logger.info("Fallback CSV empty for %s", url)
            continue

        # normalize and return
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.sort_index()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            out = df[[numeric_cols[-1]]].copy()
            return _ensure_date_fx_columns(out, numeric_cols[-1])

    return pd.DataFrame(columns=["date","fx"])


def fetch_fallback_leer():
    headers = {"User-Agent":"Mozilla/5.0"}
    url = "https://stooq.com/q/d/l/?s=eurusd&i=d"
    resp = requests.get(url, timeout=15, headers=headers)
    resp.raise_for_status()
    print(resp.status_code, resp.headers.get("content-type"))
    print(resp.text[:1000])

def fetch_fallback_for_pair(pair: str = "EURUSD=X") -> pd.DataFrame:
    """
    Versucht verlässliche Fallbacks für FX Zeitreihen in folgender Reihenfolge:
      1) frankfurter.app (key-free, ECB-based daily rates)
      2) exchangerate.host (timeseries, optional mit access_key)
      3) Yahoo CSV download (sekundär, anfällig für Auth/Crumb)
    Liefert DataFrame mit ['date','fx'] oder ein leeres DataFrame.
    Erwartet: vorhandene globale Hilfsfunktionen/Variablen:
      - wait_for_rate_slot()
      - _safe_read_csv_text(text) -> DataFrame | raises ValueError
      - _ensure_date_fx_columns(df, price_col) -> DataFrame with ['date','fx']
      - logger (logging.Logger)
    """
    # Zeitbereich: 1 Jahr
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(days=365)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    start_ts = int(start_dt.replace(tzinfo=datetime.timezone.utc).timestamp())
    end_ts = int(end_dt.replace(tzinfo=datetime.timezone.utc).timestamp())

    raw = pair.replace("=X", "").upper()
    base = raw[:3]
    quote_sym = raw[3:6] if len(raw) >= 6 else raw[3:]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1) frankfurter.app (key-free, ECB-based daily rates)
    try:
        wait_for_rate_slot()
        frank_url = f"https://api.frankfurter.app/{start_str}..{end_str}?from={base}&to={quote_sym}"
        resp = requests.get(frank_url, timeout=15, headers=headers)
        resp.raise_for_status()

        logger.debug("Fallback response %s %s %s", frank_url, resp.status_code, resp.headers.get("content-type"))
        preview = resp.text[:1000].replace("\n", "\\n")
        logger.debug("Preview: %s", preview)

        j = resp.json()
        rates = j.get("rates", {})
        if rates:
            rows = []
            for d, vals in sorted(rates.items()):
                val = vals.get(quote_sym)
                if val is not None:
                    rows.append({"date": d, "fx": float(val)})
            if rows:
                df = pd.DataFrame(rows)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                return df[["date", "fx"]]
    except Exception as e:
        logger.debug("frankfurter.app fallback failed for %s: %s", pair, e)

    # 2) exchangerate.host (optional, requires access_key for some accounts)
    EXCHANGERATE_HOST_KEY = os.getenv("EXCHANGERATE_HOST_KEY", "") or None
    if EXCHANGERATE_HOST_KEY:
        try:
            wait_for_rate_slot()
            url = (
                f"https://api.exchangerate.host/timeseries?start_date={start_str}"
                f"&end_date={end_str}&base={base}&symbols={quote_sym}&access_key={EXCHANGERATE_HOST_KEY}"
            )
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()

            logger.debug("Fallback response %s %s %s", url, resp.status_code, resp.headers.get("content-type"))
            preview = resp.text[:1000].replace("\n", "\\n")
            logger.debug("Preview: %s", preview)

            j = resp.json()
            if j.get("success"):
                rates = j.get("rates", {})
                rows = []
                for d, vals in sorted(rates.items()):
                    val = vals.get(quote_sym)
                    if val is not None:
                        rows.append({"date": d, "fx": float(val)})
                if rows:
                    df = pd.DataFrame(rows)
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.sort_values("date").reset_index(drop=True)
                    return df[["date", "fx"]]
        except Exception as e:
            logger.debug("exchangerate.host (with key) failed for %s: %s", pair, e)

    # 3) Yahoo CSV download (sekundär, kann 401/403/empty liefern)
    try:
        wait_for_rate_slot()
        yahoo_symbol = quote(pair)  # e.g. EURUSD%3DX
        yahoo_url = (
            "https://query1.finance.yahoo.com/v7/finance/download/"
            f"{yahoo_symbol}?period1={start_ts}&period2={end_ts}&interval=1d&events=history&includeAdjustedClose=true"
        )
        resp = requests.get(yahoo_url, timeout=20, headers=headers)
        resp.raise_for_status()

        logger.debug("Fallback response %s %s %s", yahoo_url, resp.status_code, resp.headers.get("content-type"))
        preview = resp.text[:1000].replace("\n", "\\n")
        logger.debug("Preview: %s", preview)

        ct = (resp.headers.get("content-type") or "").lower()
        if "text/csv" in ct or "<html" not in resp.text.lower():
            try:
                df = _safe_read_csv_text(resp.text)
            except ValueError:
                logger.debug("Yahoo CSV parse failed for %s", yahoo_url)
                df = None
            if df is not None and not df.empty:
                df.index = pd.to_datetime(df.index, errors="coerce")
                df = df.sort_index()
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                if numeric_cols:
                    out = df[[numeric_cols[-1]]].copy()
                    return _ensure_date_fx_columns(out, numeric_cols[-1])
    except Exception as e:
        logger.debug("Yahoo fallback failed for %s: %s", pair, e)

    # Alle Fallbacks fehlgeschlagen
    logger.warning("All HTTP fallbacks failed for %s", pair)
    return pd.DataFrame(columns=["date", "fx"])

    
if __name__ == "__main__":
    df = fetch_fallback_for_pair("EURUSD=X")
    print(df.head())
    print("-------------------")
    fetch_fallback_leer()
