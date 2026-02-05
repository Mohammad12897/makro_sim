#core/backend/radar_builder.py
import pandas as pd
from core.visualization.radar_plotly_country import plot_country_radar
from core.visualization.radar_plotly_etf import plot_etf_radar
from core.visualization.radar_plotly_portfolio import plot_portfolio_radar
from core.visualization.lexicon import get_lexicon, get_bitcoin_lexicon
from core.data.macro import get_country_macro
from core.data.etf import get_etf_metrics
from core.data.portfolio import get_portfolio_metrics
from core.utils.normalize import normalize_metrics_list
from core.utils.pdf import export_radar_pdf
from core.data.assets import get_asset_metrics, get_bitcoin_metrics
from core.visualization.radar_plotly_assets import plot_asset_radar


import traceback

def scan_assets(asset_string, profile):

    if not asset_string:
        return pd.DataFrame({"Fehler": ["Keine Assets eingegeben"]}), None

    symbols = [s.strip().upper() for s in asset_string.split(",")]

    rows = []

    for symbol in symbols:
        if symbol == "BTC-USD":
            metrics = get_bitcoin_metrics()
        else:
            metrics = get_asset_metrics(symbol)

        if metrics is not None:
            rows.append(metrics)

    if not rows:
        return pd.DataFrame({"Fehler": ["Keine gültigen Assets gefunden"]}), None

    df = pd.DataFrame(rows)

    # KI‑Score berechnen
    df = compute_ki_score(df, profile)

    df = df.sort_values("ki_score", ascending=False)

    fig = plot_asset_radar(rows, mode="experte")

    return df, fig


def compute_ki_score(df, profile):

    profiles = {
        "stabil": {"sharpe": 0.40, "volatility_90d": -0.30, "max_drawdown": -0.20, "trend_sma_ratio": 0.10},
        "momentum": {"trend_sma_ratio": 0.40, "performance_1y": 0.30, "performance_3y": 0.20, "sharpe": 0.10},
        "value": {"sharpe": 0.20, "performance_3y": 0.10, "volatility_90d": -0.20, "max_drawdown": -0.20, "trend_sma_ratio": 0.10},
        "growth": {"performance_1y": 0.40, "performance_3y": 0.30, "trend_sma_ratio": 0.20, "sharpe": 0.10},
        "diversifikation": {"correlation_spy": -0.40, "correlation_gold": -0.40, "volatility_90d": -0.10, "sharpe": 0.10},
        "krypto": {"trend_sma_ratio": 0.50, "performance_1y": 0.30, "volatility_90d": -0.20},
        "etf": {"performance_3y": 0.30, "sharpe": 0.30, "volatility_90d": -0.20, "max_drawdown": -0.20},
        "ki": {"sharpe": 0.35, "performance_1y": 0.20, "performance_3y": 0.10, "trend_sma_ratio": 0.15, "volatility_90d": -0.10, "max_drawdown": -0.10}
    }

    w = profiles.get(profile, profiles["ki"])

    df["ki_score"] = 0

    for key, weight in w.items():
        if key in df.columns:
            df["ki_score"] += df[key].fillna(0) * weight

    return df

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


def build_portfolio_radar(portfolio_name: str, mode: str):
    """
    Baut das Portfolio-Radar + Tabelle + Lexikon + PDF-Pfad.
    Rückgabe: fig, df_metrics, df_lexicon, pdf_path
    """
    try:
        metrics = get_portfolio_metrics(portfolio_name)
        if not metrics:
            return None, pd.DataFrame(), pd.DataFrame(), None

        # ggf. Normierung, falls du sie hier brauchst
        rows = [metrics]
        rows = normalize_metrics_list(rows, scope="portfolio")
        df_metrics = pd.DataFrame(rows)

        fig = plot_portfolio_radar(rows, mode=mode)
        lex = get_lexicon("portfolio", mode=mode)
        df_lex = pd.DataFrame(lex)

        pdf_path = export_radar_pdf(fig, metrics, portfolio_name, mode)

        return fig, df_metrics, df_lex, pdf_path

    except Exception as e:
        print("Fehler in build_portfolio_radar:", e)
        return None, pd.DataFrame({"Fehler": [str(e)]}), pd.DataFrame(), None


def build_asset_radar(selected_assets, custom_symbol, mode):

    assets = list(selected_assets) if selected_assets else []

    if custom_symbol and custom_symbol.strip():
        assets.append(custom_symbol.strip().upper())

    assets = list(set(assets))

    rows = []
    lexicon_rows = []

    for symbol in assets:
        if symbol == "BTC-USD":
            metrics = get_bitcoin_metrics()
            lex = get_bitcoin_lexicon()
        else:
            metrics = get_asset_metrics(symbol)
            lex = [{"Kennzahl": "Allgemein", "Beschreibung": f"Kennzahlen für {symbol}"}]

        if metrics is None:
            continue

        rows.append(metrics)
        lexicon_rows.extend(lex)

    if not rows:
        return None, pd.DataFrame({"Fehler": ["Keine gültigen Assets gefunden"]}), pd.DataFrame()

    fig = plot_asset_radar(rows, mode)
    df_metrics = pd.DataFrame(rows)
    df_lex = pd.DataFrame(lexicon_rows)

    return fig, df_metrics, df_lex
