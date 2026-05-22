# scripts/check_ticker.py
import sys
import yfinance as yf

def test_ticker(base):
    # Kandidaten: probiere verschiedene Suffixe
    candidates = [
        base,
        base.replace(".DE", ""),
        base.replace(".DE", ".L"),
        base.replace(".DE", ".PA"),
        base.replace(".DE", ".MI"),
        base.replace(".DE", ".US"),
        base.replace(".DE", ".AX"),
    ]
    seen = []
    for t in candidates:
        if t in seen:
            continue
        seen.append(t)
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            hist = tk.history(period="5d")
            ok = bool(info and len(hist) > 0)
        except Exception as e:
            ok = False
            info = {"error": str(e)}
            hist = None
        print(f"{t:15} -> {'OK' if ok else 'NO DATA'}")
        if ok:
            # kurze Info ausgeben
            name = info.get('shortName') or info.get('longName') or info.get('symbol') or 'unknown'
            tz = info.get('exchangeTimezoneName') or info.get('exchangeTimezoneShortName') or 'no-tz'
            print(f"    Name: {name}")
            print(f"    Timezone: {tz}")
            print(f"    Last close: {hist['Close'].iloc[-1] if hist is not None and len(hist)>0 else 'n/a'}")
        else:
            # falls Fehler vorhanden
            if isinstance(info, dict) and info.get("error"):
                print(f"    Error: {info.get('error')}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_ticker.py <BASE_TICKER>   e.g. python scripts/check_ticker.py XUDE.DE")
        sys.exit(1)
    base = sys.argv[1].strip()
    sys.exit(test_ticker(base))

