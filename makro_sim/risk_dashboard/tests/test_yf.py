import yfinance as yf
import requests
import pandas as pd

#ticker = "EUNL.DE"
ticker = "CSPX.L"

print("== Python / pandas / yfinance Versions ==")
import sys
print("python", sys.version.split()[0])
print("pandas", pd.__version__)
import yfinance
print("yfinance", yfinance.__version__)

print("\n== Direct HTTP check to Yahoo download endpoint ==")
url = "https://query1.finance.yahoo.com/v7/finance/download/EUNL.DE?period1=1451606400&period2=1704067200&interval=1d&events=history&includeAdjustedClose=true"
try:
    r = requests.get(url, timeout=10)
    print("HTTP status:", r.status_code)
    print("Content starts:", r.text[:200].replace("\n", "\\n"))
except Exception as e:
    print("HTTP error:", repr(e))

print("\n== yf.download (period=10y) ==")
try:
    df = yf.download(ticker, period="10y", auto_adjust=True, progress=False)
    print("download shape:", None if df is None else df.shape)
    if df is not None and not df.empty:
        print("First index:", df.index.min(), "Last index:", df.index.max())
    else:
        print("download returned empty")
except Exception as e:
    print("download error:", repr(e))

print("\n== yf.Ticker.history (period=10y) ==")
try:
    t = yf.Ticker(ticker)
    df2 = t.history(period="10y", auto_adjust=True)
    print("history shape:", None if df2 is None else df2.shape)
    if df2 is not None and not df2.empty:
        print("First index:", df2.index.min(), "Last index:", df2.index.max())
    else:
        print("history returned empty")
except Exception as e:
    print("history error:", repr(e))

