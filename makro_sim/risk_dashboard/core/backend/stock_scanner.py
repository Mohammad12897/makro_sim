# core/backend/stock_scanner.py

import yfinance as yf
import pandas as pd
from core.data.logging import logger

def fetch_stock_fundamentals(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            "symbol": symbol,
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "peg_ratio": info.get("pegRatio"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "free_cashflow": info.get("freeCashflow"),
        }

    except Exception as e:
        logger.error(f"Error fetching fundamentals for {symbol}: {e}")
        return None


def scan_stocks(symbols: list[str]):
    rows = []
    for s in symbols:
        data = fetch_stock_fundamentals(s)
        if data:
            rows.append(data)

    if not rows:
        return pd.DataFrame({"Fehler": ["Keine Aktien-Daten gefunden"]})

    return pd.DataFrame(rows)
