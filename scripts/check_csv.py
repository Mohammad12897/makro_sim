# scripts/check_csv.py
from pathlib import Path
import sys
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("check_csv")

from risk_dashboard.core.holdings import load_holdings_with_fallback
from risk_dashboard.ui.profiles_ui import load_price_data

HOLDINGS_DIR = PROJECT_ROOT / "risk_dashboard" / "data" / "holdings"

def main():
    etf = "EQQQ.L"
    df_key = f"holdings_{etf}"

    hdf = load_holdings_with_fallback(etf, category="", isin=None, df_key=df_key, holdings_dir=HOLDINGS_DIR)
    print("hdf shape", getattr(hdf, "shape", None))
    print(hdf.head())

    etf_universe_dict = {t: {"ticker": t} for t in hdf["ticker"].unique()}
    logger.debug("etf_universe_dict keys: %s", list(etf_universe_dict.keys()))

    try:
        prices = load_price_data(etf_universe_dict)
    except Exception as e:
        logger.exception("load_price_data failed: %s", e)
        price_path = PROJECT_ROOT / "risk_dashboard" / "data" / "price_data.csv"
        prices = pd.read_csv(price_path, parse_dates=True, index_col=0)

    print("price cols sample:", list(prices.columns)[:20])
    print("intersection:", set(hdf["ticker"]).intersection(set(prices.columns)))

if __name__ == "__main__":
    main()
