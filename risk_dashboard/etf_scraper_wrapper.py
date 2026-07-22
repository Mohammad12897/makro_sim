# risk_dashboard/etf_scraper_wrapper.py
import pandas as pd
import streamlit as st

def get_etf_meta_df(tickers):
    """
    Liefert DataFrame index=ticker mit Spalten TER (in %), AUM_mio.
    Wenn etf_scraper nicht verfügbar, gibt leeres DF zurück.
    """
    try:
        from etf_scraper import ETFScraper # type: ignore
    except Exception:
        return pd.DataFrame(index=tickers, data={"TER":[None]*len(tickers), "AUM_mio":[None]*len(tickers)})

    rows = []
    for t in tickers:
        try:
            s = ETFScraper()
            meta = s.query_meta(t)  # falls API so heißt; passe an
            ter = meta.get("TER")   # passe Feldnamen an
            aum = meta.get("AUM_mio")
            rows.append({"ticker": t, "TER": ter, "AUM_mio": aum})
        except Exception:
            rows.append({"ticker": t, "TER": None, "AUM_mio": None})
    df = pd.DataFrame(rows).set_index("ticker")
    return df
