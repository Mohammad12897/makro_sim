# scripts/check_meta.py
import sys
import yfinance as yf

def check(ticker):
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    print("Ticker:", ticker)
    print("shortName:", info.get("shortName"))
    print("exchange:", info.get("exchange"))
    print("exchangeTimezoneName:", info.get("exchangeTimezoneName"))
    try:
        hist = tk.history(period="5d")
        print("history rows:", len(hist))
    except Exception as e:
        print("history error:", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_meta.py <TICKER>")
        sys.exit(1)
    check(sys.argv[1])
