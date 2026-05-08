# core/backend/isin_database.py
import json
from pathlib import Path

ISIN_DB_FILE = Path("core/data/isin_database.json")

INITIAL_DB = {
    "AAPL": "US0378331005",
    "MSFT": "US5949181045",
    "GOOGL": "US02079K3059",
    "AMZN": "US0231351067",
    "TSLA": "US88160R1014",
    "SPY": "US78462F1030",
    "EUNL.DE": "IE00B4L5Y983",
    "VWCE.DE": "IE00BK5BQT80",
    "BMW.DE": "DE0005190003",
    "SAP.DE": "DE0007164600",
    "BTC-USD": None
}

def load_isin_db():
    if not ISIN_DB_FILE.exists():
        ISIN_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        ISIN_DB_FILE.write_text(json.dumps(INITIAL_DB, indent=2))
        return INITIAL_DB
    return json.loads(ISIN_DB_FILE.read_text())

def save_isin_db(db):
    ISIN_DB_FILE.write_text(json.dumps(db, indent=2))
    
ISIN_DATABASE = {

    # -------------------------
    # US-Aktien (Large Cap)
    # -------------------------
    "AAPL": "US0378331005",
    "MSFT": "US5949181045",
    "GOOGL": "US02079K3059",
    "GOOG": "US02079K1079",
    "AMZN": "US0231351067",
    "META": "US30303M1027",
    "TSLA": "US88160R1014",
    "NVDA": "US67066G1040",
    "BRK.B": "US0846707026",
    "BRK.A": "US0846701086",
    "JPM": "US46625H1005",
    "V": "US92826C8394",
    "MA": "US57636Q1040",
    "HD": "US4370761029",
    "PG": "US7427181091",
    "KO": "US1912161007",
    "PEP": "US7134481081",
    "NFLX": "US64110L1061",
    "INTC": "US4581401001",
    "CSCO": "US17275R1023",
    "ADBE": "US00724F1012",
    "CRM": "US79466L3024",
    "PYPL": "US70450Y1038",
    "DIS": "US2546871060",
    "MCD": "US5801351017",
    "NKE": "US6541061031",
    "XOM": "US30231G1022",
    "CVX": "US1667641005",
    "WMT": "US9311421039",
    "T": "US00206R1023",
    "VZ": "US92343V1044",
    "IBM": "US4592001014",

    # -------------------------
    # Deutsche Aktien (DAX)
    # -------------------------
    "SAP.DE": "DE0007164600",
    "BMW.DE": "DE0005190003",
    "BAS.DE": "DE000BASF111",
    "ALV.DE": "DE0008404005",
    "VOW3.DE": "DE0007664039",
    "DTE.DE": "DE0005557508",
    "SIE.DE": "DE0007236101",
    "ADS.DE": "DE000A1EWWW0",
    "BAYN.DE": "DE000BAY0017",
    "LIN.DE": "IE00BZ12WP82",
    "RWE.DE": "DE0007037129",
    "DBK.DE": "DE0005140008",
    "HEN3.DE": "DE0006048432",
    "MRK.DE": "DE0006599905",

    # -------------------------
    # Europäische Aktien
    # -------------------------
    "NESN.SW": "CH0038863350",
    "NOVN.SW": "CH0012005267",
    "ASML.AS": "NL0010273215",
    "AD.AS": "NL0000009827",
    "SAN.PA": "FR0000120578",
    "OR.PA": "FR0000120321",
    "AIR.PA": "NL0000235190",

    # -------------------------
    # ETFs – USA
    # -------------------------
    "SPY": "US78462F1030",
    "VOO": "US9229083632",
    "IVV": "US4642872000",
    "QQQ": "US46090E1038",
    "IWM": "US4642876555",
    "DIA": "US78467X1090",
    "IEMG": "US46434G1031",
    "AGG": "US4642872265",
    "TLT": "US4642874329",

    # -------------------------
    # ETFs – Europa
    # -------------------------
    "EUNL.DE": "IE00B4L5Y983",
    "VWCE.DE": "IE00BK5BQT80",
    "CSPX.L": "IE00B5BMR087",
    "SXR8.DE": "IE00B4L5Y983",
    "IUSQ.DE": "IE00BYX2JD69",
    "XDWD.DE": "IE00BK5BQT80",
    "EQQQ.L": "IE0032077012",
    "EMIM.L": "IE00BKM4GZ66",

    # -------------------------
    # Rohstoffe (ETCs)
    # -------------------------
    "GLD": "US78463V1070",
    "SLV": "US78468R1014",
    "PPLT": "US69318Q1058",
    "CPER": "US73936B2007",

    # -------------------------
    # Kryptowährungen (keine ISIN)
    # -------------------------
    "BTC-USD": None,
    "ETH-USD": None,
    "SOL-USD": None,
    "ADA-USD": None,
    "XRP-USD": None,
}
