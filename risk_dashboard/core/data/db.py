# core/data/db.py

def load_etf_db():
    """
    Beispielhafte ETF-Datenbank.
    Später kannst du echte Datenquellen anbinden.
    """
    return [
        {
            "ticker": "SPY",
            "1Y %": 22.4,
            "5Y %": 78.1,
            "Volatilität %": 17.2,
            "Sharpe": 1.35,
            "TER": 0.09,
            "Tracking Error": 0.35,
            "AUM": 450_000_000_000,
            "DivRendite %": 1.4,
        },
        {
            "ticker": "QQQ",
            "1Y %": 28.1,
            "5Y %": 110.4,
            "Volatilität %": 22.5,
            "Sharpe": 1.45,
            "TER": 0.20,
            "Tracking Error": 0.40,
            "AUM": 220_000_000_000,
            "DivRendite %": 0.7,
        },
        # weitere ETFs...
    ]
