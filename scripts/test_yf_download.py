# scripts/test_yf_download.py
# python scripts/test_yf_download.py
import time
from datetime import datetime as dt
import pytz
import yfinance as yf

TICKER = "EXS1.DE"
TZ = "Europe/Berlin"
RETRIES = 3
RETRY_BASE_SLEEP = 0.5  # Sekunden

def download_with_tz_and_fallback(ticker_symbol: str):
    tz = pytz.timezone(TZ)
    start = tz.localize(dt(2018, 1, 1))
    end = tz.localize(dt.now())

    # Versuch 1..RETRIES: ticker.history (falls du ein Ticker-Objekt bevorzugst)
    for attempt in range(1, RETRIES + 1):
        try:
            print(f"[attempt {attempt}] history() für {ticker_symbol} ...")
            t = yf.Ticker(ticker_symbol)
            df = t.history(start=start, end=end, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                print(f"[attempt {attempt}] history() erfolgreich, {len(df)} Zeilen.")
                return df
            print(f"[attempt {attempt}] history() lieferte keine Daten, versuche fallback.")
        except Exception as e:
            print(f"[attempt {attempt}] history() Exception: {e!r}")

        # Exponentielles Backoff
        time.sleep(RETRY_BASE_SLEEP * (2 ** (attempt - 1)))

    # Fallback: yf.download
    try:
        print("Fallback: yf.download() ...")
        df = yf.download(ticker_symbol, start=start, end=end, auto_adjust=True, progress=False)
        if df is not None and not df.empty:
            print(f"yf.download() erfolgreich, {len(df)} Zeilen.")
            return df
        print("yf.download() lieferte keine Daten.")
    except Exception as e:
        print(f"yf.download() Exception: {e!r}")

    # Wenn alles fehlschlägt, None zurückgeben
    return None

if __name__ == "__main__":
    print("Starte Test für yfinance Download mit Zeitzone und Retries")
    df = download_with_tz_and_fallback(TICKER)
    if df is None:
        print(f"Kein Daten‑Frame für {TICKER} erhalten.")
    else:
        print(df.tail(5))
