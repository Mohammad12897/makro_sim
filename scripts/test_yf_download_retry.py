# scripts/test_yf_download_retry.py
# python scripts/test_yf_download_retry.py
import time
import random
from datetime import datetime as dt
import pytz
import yfinance as yf

TICKER = "EXS1.DE"
TZ = "Europe/Berlin"
RETRIES = 5
BASE_SLEEP = 0.5  # Sekunden, Basis für Backoff

def download_with_backoff(ticker_symbol: str):
    tz = pytz.timezone(TZ)
    start = tz.localize(dt(2018, 1, 1))
    end = tz.localize(dt.now())

    # Versuche mit Ticker.history (falls bevorzugt)
    for attempt in range(1, RETRIES + 1):
        try:
            print(f"[attempt {attempt}] Ticker.history() für {ticker_symbol} ...")
            t = yf.Ticker(ticker_symbol)
            df = t.history(start=start, end=end, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                print(f"[attempt {attempt}] history() erfolgreich, {len(df)} Zeilen.")
                return df
            print(f"[attempt {attempt}] history() lieferte keine Daten.")
        except Exception as e:
            print(f"[attempt {attempt}] history() Exception: {e!r}")

        # Exponentielles Backoff + zufälliges Jitter
        sleep = BASE_SLEEP * (2 ** (attempt - 1))
        sleep = sleep * (0.8 + 0.4 * random.random())  # ±20% Jitter
        print(f"Sleeping {sleep:.2f}s before next attempt...")
        time.sleep(sleep)

    # Fallback: yf.download (Batch‑friendly)
    try:
        print("Fallback: yf.download() ...")
        df = yf.download(ticker_symbol, start=start, end=end, auto_adjust=True, progress=False)
        if df is not None and not df.empty:
            print(f"yf.download() erfolgreich, {len(df)} Zeilen.")
            return df
        print("yf.download() lieferte keine Daten.")
    except Exception as e:
        print(f"yf.download() Exception: {e!r}")

    return None

if __name__ == "__main__":
    print("Starte Test mit Backoff/Jitter und Fallback")
    df = download_with_backoff(TICKER)
    if df is None:
        print(f"Kein DataFrame für {TICKER} erhalten (Rate limit oder kein Data).")
    else:
        print(df.tail(5))
