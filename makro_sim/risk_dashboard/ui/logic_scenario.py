#ui/logic_scenario.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from core.data.assets import fetch_price_history

def ui_scenario_comparison(ticker_text, scenario):
    shock_map = {
        "Rezession": -0.15,
        "Inflation": -0.10,
        "Zinsanstieg": -0.20,
        "Ölkrise": -0.12
    }

    # Szenario-Schock bestimmen
    shock = shock_map.get(scenario, 0)

    # Ticker-Liste aufsplitten
    tickers = [t.strip() for t in ticker_text.split(",") if t.strip()]

    rows = []
    for t in tickers:
        series = fetch_price_history(t, period="1y")

        if series is None or len(series) == 0:
            rows.append([t, "Keine Daten", "Keine Daten"])
            continue

        last = series.iloc[-1]
        shocked = last * (1 + shock)

        rows.append([t, last, shocked])

    return pd.DataFrame(rows, columns=["Ticker", "Aktuell", "Nach Szenario"])
