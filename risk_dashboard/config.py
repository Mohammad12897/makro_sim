# risk_dashboard/config.py
from datetime import date
import pandas as pd
import os


# config.py
ALLOW_TEST_UNIVERSE = os.getenv("RISK_DASHBOARD_ALLOW_TEST_UNIVERSE", "false").lower() == "true"

UNIVERSE_PATHS = {
    "EURO STOXX 50": "risk_dashboard/data/universe_eurostoxx.yaml",
    "NASDAQ 100": "risk_dashboard/data/universe_nasdaq.yaml",
    "Nikkei 225": "risk_dashboard/data/universe_nikkei.yaml",
}


# Strings als Canonical Defaults (lesbar in Configs)
DEFAULT_START_STR = "2016-01-01"
DEFAULT_END_STR = date.today().isoformat()

# Pandas Timestamps für interne Verwendung
DEFAULT_START = pd.to_datetime(DEFAULT_START_STR)
DEFAULT_END = pd.to_datetime(DEFAULT_END_STR)
# Optional: explizit exportieren
__all__ = ["DEFAULT_START_STR", "DEFAULT_END_STR", "DEFAULT_START", "DEFAULT_END"]

# risk_dashboard/config.py (erweitern)
# Optional: vordefinierte ETF Kandidaten pro Index (kann vom Nutzer angepasst werden)
# Format: { "INDEX_NAME": [ {"ticker":"VWRL","name":"Vanguard FTSE All-World", "domicile":"IE", "expense_ratio":0.22, "aum":None, "replication":"physical"}, ... ] }
ETF_CANDIDATES = {
    # Beispiel
    "GLOBAL": [
        {"ticker": "VWRL", "name": "Vanguard FTSE All-World", "domicile": "IE", "expense_ratio": 0.22, "aum": None, "replication": "physical"}
    ]
}
