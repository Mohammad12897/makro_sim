# core/backend/etf_scanner.py

import requests
import pandas as pd
from bs4 import BeautifulSoup
from core.data.logging import logger

JUSTETF_URL = "https://www.justetf.com/de/etf-profile.html?isin="

def fetch_justetf_data(isin: str):
    url = JUSTETF_URL + isin
    logger.info(f"Fetching justETF data for {isin}")

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            logger.warning(f"justETF returned status {r.status_code} for {isin}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        def extract(label):
            el = soup.find("dt", string=label)
            if not el:
                return None
            val = el.find_next("dd").text.strip()
            return val

        return {
            "isin": isin,
            "ter": extract("Gesamtkostenquote (TER)"),
            "fund_size": extract("Fondsvolumen"),
            "replication": extract("Replikationsmethode"),
            "tracking_diff": extract("Tracking-Differenz"),
            "domicile": extract("Domizil"),
            "fund_currency": extract("Fondswährung"),
        }

    except Exception as e:
        logger.error(f"Error scraping justETF for {isin}: {e}")
        return None


def scan_etf_list(isins: list[str]):
    rows = []
    for isin in isins:
        data = fetch_justetf_data(isin)
        if data:
            rows.append(data)

    if not rows:
        return pd.DataFrame({"Fehler": ["Keine ETF-Daten gefunden"]})

    df = pd.DataFrame(rows)
    return df
