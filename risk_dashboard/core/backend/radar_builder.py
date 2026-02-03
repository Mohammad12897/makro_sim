#core/backend/radar_builder.py
import pandas as pd
from core.visualization.radar_plotly_country import plot_country_radar
from core.visualization.radar_plotly_etf import plot_etf_radar
from core.visualization.radar_plotly_portfolio import plot_portfolio_radar
from core.visualization.lexicon import get_lexicon
from core.data.macro import get_country_macro
from core.data.etf import get_etf_metrics
from core.data.portfolio import get_portfolio_metrics
from core.utils.normalize import normalize_metrics_list
from core.utils.pdf import export_radar_pdf

import traceback

def build_country_radar(countries, mode):
    try:
        if not countries:
            return None, pd.DataFrame(), pd.DataFrame()

        rows = []
        for c in countries:
            macro = get_country_macro(c)
            macro["country"] = c
            rows.append(macro)

        rows = normalize_metrics_list(rows, scope="laender")
        fig = plot_country_radar(rows, mode=mode)
        lex = get_lexicon("laender", mode=mode)

        return fig, pd.DataFrame(rows), pd.DataFrame(lex)

    except Exception as e:
        print("Fehler in build_country_radar:", e)
        return None, pd.DataFrame({"Fehler": [str(e)]}), pd.DataFrame()


def build_etf_radar(etfs, mode):
    if not etfs:
        return None, pd.DataFrame(), pd.DataFrame()

    rows = []
    for t in etfs:
        metrics = get_etf_metrics(t)  # dict mit 1Y %, 5Y %, Volatilität %, Sharpe, TER, Tracking Error, AUM, DivRendite %
        metrics["ticker"] = t
        rows.append(metrics)

    rows = normalize_metrics_list(rows, scope="etf")
    fig = plot_etf_radar(rows, mode=mode)
    lex = get_lexicon("etf", mode=mode)

    return fig, pd.DataFrame(rows), pd.DataFrame(lex)


def build_portfolio_radar(portfolio_name, mode):
    # hier kannst du später echte Portfolio-Daten einhängen
    metrics = get_portfolio_metrics(portfolio_name)  # dict mit Gewichteter Sharpe, Gewichtete Volatilität, 1Y %, 5Y %, Diversifikation, Region-Exposure
    metrics["portfolio_name"] = portfolio_name
    rows = [metrics]

    rows = normalize_metrics_list(rows, scope="portfolio")
    fig = plot_portfolio_radar(rows, mode=mode)
    lex = get_lexicon("portfolio", mode=mode)

    pdf_bytes = export_radar_pdf(fig, metrics, portfolio_name, mode)

    return fig, pd.DataFrame(rows), pd.DataFrame(lex), pdf_bytes
