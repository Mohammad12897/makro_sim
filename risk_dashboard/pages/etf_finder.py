# risk_dashboard/pages/etf_finder.py
import os
import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

logger = logging.getLogger("risk_dashboard.pages.etf_finder")
# Lokale Hilfsfunktionen

from risk_dashboard.data_cache import load_price_data_cached


# Optional: falls du Metadaten scrapen willst
# from etf_scraper import ETFScraper

st.set_page_config(page_title="ETF Finder", layout="wide")


def compute_metrics(price_df):
    # sicherstellen, dass price_df ein DataFrame ist
    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame()

    price_df = price_df.ffill().bfill().dropna(axis=1, how="all")
    rets = price_df.pct_change().dropna(how="all")
    ann_ret = (1 + rets.mean()) ** 252 - 1
    ann_vol = rets.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol.replace(0, np.nan)
    momentum_12m = price_df.iloc[-1] / price_df.shift(252).iloc[-1] - 1
    # Max Drawdown per ticker
    cum = (1 + rets).cumprod()
    dd = cum.div(cum.cummax()) - 1
    max_dd = dd.min()
    metrics = pd.DataFrame({
        "CAGR": ann_ret,
        "Vol": ann_vol,
        "Sharpe": sharpe,
        "Momentum12M": momentum_12m,
        "MaxDD": max_dd
    })
    return metrics

def score_and_rank(metrics, weights=None):
    if weights is None:
        weights = {"CAGR":0.30, "Vol":-0.25, "Sharpe":0.25, "Momentum12M":0.20}
    z = (metrics - metrics.mean()) / metrics.std(ddof=0)
    # invert Vol (lower is better)
    z["Vol"] = -z["Vol"]
    score = sum(z[col] * w for col, w in weights.items() if col in z.columns)
    metrics["Score"] = score
    return metrics.sort_values("Score", ascending=False)

# --- Rebalancing / Execution helper Beispiele ---
def dca_schedule(dates, amount):
    """Gibt die Termine zurück, an denen DCA ausgeführt werden soll (z.B. 1. des Monats)."""
    monthly = [d for d in dates if d.day == 1]
    return monthly

def vol_target_leverage(portfolio_returns, target_vol=0.10, cap=2.0):
    """Berechnet Hebel basierend auf aktueller Volatilität (rolling 63d)."""
    if portfolio_returns is None or len(portfolio_returns) < 20:
        return 1.0
    rolling_vol = portfolio_returns.rolling(window=63).std().dropna() * np.sqrt(252)
    current_vol = rolling_vol.iloc[-1] if not rolling_vol.empty else np.nan
    if np.isnan(current_vol) or current_vol == 0:
        return 1.0
    leverage = float(target_vol / current_vol)
    leverage = max(0.0, min(leverage, cap))
    return leverage


def load_meta_for_universe(tickers, path="data/etf_meta.csv"):
    df = pd.read_csv(path, index_col=0)
    return df.reindex(tickers)


# --- UI ---
st.title("ETF Finder")

with st.sidebar:
    st.header("Einstellungen")
    start_date = st.date_input("Startdatum", value=pd.to_datetime("2010-01-01"))
    ter_threshold = st.slider("Max TER (%)", 0.0, 2.0, 0.5, 0.01)
    min_aum_mio = st.number_input("Min AUM (Mio)", value=50)
    score_weights = {
        "CAGR": st.slider("Gewicht CAGR", 0.0, 1.0, 0.30, 0.05),
        "Vol": st.slider("Gewicht Vol (negativ)", -1.0, 0.0, -0.25, 0.05),
        "Sharpe": st.slider("Gewicht Sharpe", 0.0, 1.0, 0.25, 0.05),
        "Momentum12M": st.slider("Gewicht Momentum12M", 0.0, 1.0, 0.20, 0.05)
    }


st.set_page_config(page_title="ETF Finder", layout="wide")

# UI: Universe Input
tickers_input = st.text_area("Universe (ein Ticker pro Zeile)", value="VOO\nVWRL.L\nSPY\nCSPX.L")
tickers = [t.strip() for t in tickers_input.splitlines() if t.strip()]

# --- Metadaten laden (TER/AUM) einmalig, vor Preisabruf ---
try:
    from risk_dashboard.etf_scraper_wrapper import get_etf_meta_df  # optional
    meta_df = get_etf_meta_df(tickers)  # DataFrame index=ticker, cols=['TER','AUM_mio']
except Exception:
    meta_path = os.path.join("data", "etf_meta.csv")
    if os.path.exists(meta_path):
        meta_df = pd.read_csv(meta_path, index_col=0).reindex(tickers)
    else:
        meta_df = pd.DataFrame(index=tickers, data={"TER":[None]*len(tickers), "AUM_mio":[None]*len(tickers)})

# TER/AUM Filter (konservativ: None = nicht automatisch ausschließen)
ter_thresh = 0.5   # in %
min_aum_mio = 50   # in Mio
good = []
for t in tickers:
    try:
        ter = float(meta_df.loc[t, "TER"]) if pd.notna(meta_df.loc[t, "TER"]) else None
    except Exception:
        ter = None
    try:
        aum = float(meta_df.loc[t, "AUM_mio"]) if pd.notna(meta_df.loc[t, "AUM_mio"]) else None
    except Exception:
        aum = None
    if (ter is None or ter <= ter_thresh) and (aum is None or aum >= min_aum_mio):
        good.append(t)

filtered_tickers = [t for t in tickers if t in good]
if not filtered_tickers and tickers:
    st.warning("Nach TER/AUM Filter sind keine ETFs übrig. Es wird das ursprüngliche Universe verwendet.")
    filtered_tickers = tickers.copy()

# Button: Screen & Rank
if st.button("Screen & Rank"):
    if not filtered_tickers:
        st.warning("Bitte mindestens einen Ticker angeben.")
    else:
        with st.spinner("Preise laden..."):
            price_df = load_price_data_cached(filtered_tickers, start="2010-01-01")
 
        if price_df is None or price_df.empty:
            st.error("Keine Preisdaten verfügbar.")
        else:
            # compute_metrics und score_and_rank müssen in deinem Modul definiert sein
            metrics = compute_metrics(price_df)               # liefert DataFrame mit 'Momentum12M' etc.
            ranked = score_and_rank(metrics, weights=score_weights)  # score_weights aus Sidebar

            # Top N auswählen und initiale Gewichte setzen
            top_n = 10
            top_list = ranked.head(top_n).index.tolist()
            weights = {t: 1.0/len(top_list) for t in top_list} if top_list else {}

            # Momentum‑Filter anwenden (funktion in helpers oder hier definieren)
            momentum_threshold = 0.0
            momentum_12m = metrics['Momentum12M'].to_dict()

            def momentum_filter(weights, momentum_12m, threshold=0.0):
                new = {}
                for t, w in weights.items():
                    if momentum_12m.get(t, -999) > threshold:
                        new[t] = w
                    else:
                        new[t] = 0.0
                s = sum(new.values())
                if s > 0:
                    return {k: v/s for k, v in new.items()}
                else:
                    return weights

            weights = momentum_filter(weights, momentum_12m, threshold=momentum_threshold)

            # Anzeige
            st.subheader("Ranking")
            st.dataframe(ranked.style.format({
                "CAGR":"{:.2%}", "Vol":"{:.2%}", "Sharpe":"{:.2f}",
                "Momentum12M":"{:.2%}", "MaxDD":"{:.2%}", "Score":"{:.3f}"
            }))
            st.download_button("Download Ranking CSV", ranked.to_csv(index=True), file_name="etf_ranking.csv")

            # Detailchart Top 1
            if not ranked.empty:
                top = ranked.head(1).index[0]
                st.subheader(f"Top ETF: {top}")
                fig = px.line(price_df[top].ffill().bfill().reset_index(), x='Date', y=top, title=f"Price: {top}")
                #st.plotly_chart(fig, use_container_width=True)
                st.plotly_chart(fig, width="stretch")

            # Speichere Top5 und weights für Backtest
            st.session_state['etf_finder_top5'] = ranked.head(5).index.tolist()
            st.session_state['etf_finder_weights'] = weights

st.markdown("---")
st.subheader("Backtest Integration")

# Maximal gewünschte Anzahl (UI-Label passt sich automatisch an)
MAX_TOP = 5

# Versuche, Top5 und Weights aus session_state zu holen (kann None sein)
top5 = st.session_state.get("etf_finder_top5", []) or []
weights = st.session_state.get("etf_finder_weights", {})


# Stelle sicher, dass price_df definiert ist; falls nicht, lade es defensiv
if 'price_df' not in globals() or price_df is None:
    try:
        price_df = load_price_data_cached(filtered_tickers, start="2010-01-01")
    except Exception as e:
        logger.warning("load_price_data_cached failed while ensuring price_df: %s", e)
        st.error("Preisdaten konnten nicht geladen werden. Bitte überprüfe die Tickerliste.")
        price_df = pd.DataFrame()

# Bestimme, wie viele ETFs tatsächlich verfügbar sind
available_universe = [t for t in (price_df.columns.tolist() if not price_df.empty else [])]
n_available = len(available_universe)
top_n = min(MAX_TOP, n_available)

# UI Hinweise
if n_available == 0:
    st.info("Keine Preisdaten verfügbar. Wähle zuerst ETFs im Finder.")
else:
    if n_available < MAX_TOP:
        st.info(f"Nur {n_available} ETFs in den Preisdaten vorhanden — Top {n_available} wird verwendet.")

# Button-Label dynamisch
if st.button(f"Backtest Top {top_n} (aus ETF Finder)"):
    # Wenn keine Top-Auswahl vorhanden, abbrechen
    if not top5:
        st.warning("Keine Top‑Auswahl vorhanden. Bitte wähle zuerst ETFs im Finder.")
    else:
        # Importiere Backtest-Funktion hier (lokal, um zyklische Imports zu vermeiden)
        from risk_dashboard.core.macro_pipeline import run_backtest

        # Prüfe price_df
        if price_df.empty:
            st.error("Keine Preisdaten verfügbar für die ausgewählten ETFs.")
        else:
            # Begrenze top5 auf die tatsächlich vorhandenen Spalten
            # und achte auf Reihenfolge / Länge (max top_n)
            requested = top5[:MAX_TOP]
            available = [t for t in requested if t in price_df.columns]
            missing = [t for t in requested if t not in price_df.columns]

            if missing:
                logger.info("Top selection contains tickers missing in price_df: %s", missing)
                st.warning(f"Einige ausgewählte ETFs fehlen in den Preisdaten und werden ignoriert: {missing}")

            if not available:
                st.error("Kein Top‑ETF ist in den Preisdaten vorhanden. Backtest abgebrochen.")
            else:
                # Optional: trim to top_n (falls more available than top_n)
                available = available[:top_n]

                prices_subset = price_df[available]
                try:
                    result = run_backtest(
                        tickers=available,
                        prices_df=prices_subset,
                        start=start_date,
                        initial_cash=10000,
                        monthly_dca=500,
                        weights=weights
                    )
                except ValueError as e:
                    logger.warning("run_backtest failed: %s", e)
                    st.error("Backtest konnte nicht ausgeführt werden: keine gültigen Ticker in den Preisdaten.")
                    result = {}
                except Exception as e:
                    logger.exception("Unexpected error in run_backtest: %s", e)
                    st.error("Beim Backtest ist ein Fehler aufgetreten. Details im Log.")
                    result = {}
                st.write(result.get("metrics", {}))
