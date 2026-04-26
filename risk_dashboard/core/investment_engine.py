# risk_dashboard/core/investment_engine.py
from gradio.monitoring_dashboard import data
import numpy as np
import yfinance as yf
import pandas as pd
import streamlit as st
from scipy.cluster.hierarchy import linkage, leaves_list
from risk_dashboard.core.market_engine import download_etf_history, build_market_risk_factors
from risk_dashboard.core.risk_engine import compute_risk_score_v2, detect_risk_regimes, build_scenario_series
from risk_dashboard.core.macro_loader import load_macro_data
from risk_dashboard.core.utils import get_latest_before, ensure_date_column
from risk_dashboard.core.asset_packages import (
    map_regime_to_key,
    select_equity_package
)

from functools import lru_cache



@lru_cache(maxsize=32)
def load_etf_prices_monthly(tickers_tuple, period="10y"):
    tickers = list(tickers_tuple)
    prices = download_etf_history(tickers, period=period, auto_resample=True)

    if prices is None or prices.empty:
        st.error("load_etf_prices_monthly – keine Preise geladen.")
        return pd.DataFrame(), tickers

    prices = prices.ffill().dropna(how="all")
    available = [c for c in prices.columns if c in tickers]
    missing = [t for t in tickers if t not in available]

    if missing:
        st.warning(f"ETF-Loader – fehlende Ticker nach Download: {missing}")

    prices = prices[available]
    return prices, missing


def classify_scenario_from_score(score: float) -> str:
    if score < 0.25:
        return "Rezession"
    elif score < 0.45:
        return "Stagflation"
    elif score < 0.60:
        return "Soft Landing"
    elif score < 0.80:
        return "Reflation"
    else:
        return "Boom"

def load_etf_prices(tickers, start=None, end=None):
    st.write("ETF-Loader – angefragte Ticker:", tickers)

    data = yf.download(tickers, start=start, end=end, auto_adjust=True)

    st.write("ETF-Loader – rohe Daten:", data.head())

    # Fall 1: MultiIndex (mehrere Ticker)
    if isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.levels[0]:
            data = data["Adj Close"]
        else:
            st.warning("MultiIndex ohne 'Adj Close' – verwende 'Close'.")
            data = data["Close"]

    # Fall 2: SingleIndex (ein Ticker)
    else:
        if "Adj Close" in data.columns:
            data = data[["Adj Close"]]
        elif "Close" in data.columns:
            data = data[["Close"]]
        else:
            st.error("Weder 'Adj Close' noch 'Close' vorhanden.")
            return pd.DataFrame()

    # gültige Spalten extrahieren
    valid_cols = [c for c in data.columns if data[c].notna().sum() > 0]
    missing = [c for c in tickers if c not in valid_cols]

    if missing:
        st.warning(f"ETF-Loader – fehlende Ticker: {missing}")

    if not valid_cols:
        st.error("ETF-Loader – keine gültigen Preisreihen gefunden.")
        return pd.DataFrame()
    
    # ✅ Debug-Ausgabe HIER einfügen
    st.write("DEBUG – ETF Loader Zeitraum:", data.index[:5], data.index[-5:])

    return data[valid_cols]


def apply_scenario_overlay(weights, scenario):
    w = weights.copy()

    if scenario == "Rezession":
        # mehr Bonds, weniger Aktien
        for t in w:
            if "IEGA.L" in t:
                w[t] *= 1.2
            if "CSPX.L" in t or "EQQQ.L" in t:
                w[t] *= 0.8

    elif scenario == "Stagflation":
        for t in w:
            if "SGLN.L" in t:
                w[t] *= 1.2

    elif scenario == "Boom":
        for t in w:
            if "EQQQ.L" in t or "IUSN.L" in t:
                w[t] *= 1.2

    # normalisieren
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


# ---------------------------------------------------------
# BASIS: MAKRO-TRENDS & RISK LEVEL
# ---------------------------------------------------------
def detect_macro_trends():
    df = load_macro_data()

    gdp = df["gdp"].pct_change().iloc[-1]
    cpi = df["cpi"].pct_change().iloc[-1]
    unrate = df["unrate"].pct_change().iloc[-1]
    fed = df["fedfunds"].pct_change().iloc[-1]

    return {
        "gdp": gdp,
        "cpi": cpi,
        "unrate": unrate,
        "fedfunds": fed
    }



def classify_risk_level():
    """
    Risk Score 2.0 in Kategorien einteilen.
    Liefert 'low' / 'medium' / 'high' (Beispiel).
    """
    df = compute_risk_score_v2(normalize=True, method="minmax")

    # Defensive Prüfung
    if df.empty:
        # Fallback-Verhalten definieren: z.B. konservativ "high" oder raise
        # Hier: konservativ -> "high"
        return "high"

    # Priorisierte Spaltenliste (Fallbacks)
    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    col = next((c for c in preferred_cols if c in df.columns), None)
    if col is None:
        # keine Score-Spalte gefunden -> konservativer Default
        return "high"

    latest = float(df.iloc[-1][col])

    # Beispiel-Schwellen (anpassen nach Bedarf)
    if latest < 0.33:
        return "low"
    elif latest < 0.66:
        return "medium"
    else:
        return "high"


def get_latest_regime(scenario_regimes=None):
    if scenario_regimes is not None and not scenario_regimes.empty:
        regimes = scenario_regimes.copy()
    else:
        regimes = detect_risk_regimes().copy()

    regimes = regimes.dropna(subset=["regime"])
    return regimes.iloc[-1]["regime"]

def map_regime_to_label(regime_value):
    mapping = {
        0: "Risk-Off",
        1: "Neutral",
        2: "Risk-On"
    }
    return mapping.get(regime_value, "Unknown")


# ---------------------------------------------------------
# ETF-MAPPING
# ---------------------------------------------------------
def etf_mapping():
    """ETF-Mapping für jede Assetklasse (generische Typen, keine konkreten Produkte)."""
    return {
        "Growth-Aktien": ["NASDAQ-ETF", "Tech-ETF", "Innovation-ETF"],
        "Value-Aktien": ["Value-ETF", "Dividend-ETF"],
        "Defensive Aktien": ["Healthcare-ETF", "Utilities-ETF"],
        "Zyklische Aktien": ["Industrie-ETF", "Konsum-ETF"],
        "Kurzläufer-Anleihen": ["Short-Term Bond ETF"],
        "Langläufer-Anleihen": ["Long-Term Treasury ETF"],
        "Gold": ["Gold-ETF"],
        "Rohstoffe": ["Commodity-ETF", "Energy-ETF"],
        "Geldmarkt": ["Money Market ETF"]
    }


# ---------------------------------------------------------
# A) REGIME-BASIERTE HANDELSSTRATEGIE
# ---------------------------------------------------------
def regime_based_strategy():
    """Regime-basierte Handelslogik: welche Assetklassen werden in welchem Regime bevorzugt."""
    regime = get_latest_regime()

    if regime == "High Risk":
        assets = [
            "Defensive Aktien",
            "Kurzläufer-Anleihen",
            "Gold",
            "Geldmarkt"
        ]
    elif regime == "Medium Risk":
        assets = [
            "Value-Aktien",
            "Defensive Aktien",
            "Kurzläufer-Anleihen",
            "Gold"
        ]
    else:  # Low Risk
        assets = [
            "Growth-Aktien",
            "Zyklische Aktien",
            "Langläufer-Anleihen",
            "Rohstoffe"
        ]

    return {
        "regime": regime,
        "preferred_assets": assets
    }


# ---------------------------------------------------------
# B) ETF-SCREENING BASIEREND AUF MAKRO-REGIMEN
# ---------------------------------------------------------
def etf_screening_by_regime():
    """Leitet aus dem Regime passende ETF-Typen ab."""
    strategy = regime_based_strategy()
    mapping = etf_mapping()

    etfs = {}
    for asset in strategy["preferred_assets"]:
        etfs[asset] = mapping.get(asset, [])

    return {
        "regime": strategy["regime"],
        "assets": strategy["preferred_assets"],
        "etfs": etfs
    }


# ---------------------------------------------------------
# C) PORTFOLIO-OPTIMIERUNG MIT RISIKO-BUDGET (REGELBASIERT)
# ---------------------------------------------------------
def portfolio_weights(risk_level, regime, risk_budget: float = 1.0):
    """
    Regelbasierte Portfolio-Gewichtung.
    risk_budget ist hier ein Skalierungsfaktor (0..1), könnte später mit Volatilitäten verknüpft werden.
    """
    if risk_level == "high" or regime == "High Risk":
        base = {
            "Defensive Aktien": 0.20,
            "Kurzläufer-Anleihen": 0.30,
            "Gold": 0.25,
            "Geldmarkt": 0.25
        }
    elif risk_level == "medium" or regime == "Medium Risk":
        base = {
            "Value-Aktien": 0.30,
            "Kurzläufer-Anleihen": 0.25,
            "Gold": 0.15,
            "Zyklische Aktien": 0.30
        }
    else:  # low risk
        base = {
            "Growth-Aktien": 0.40,
            "Zyklische Aktien": 0.30,
            "Langläufer-Anleihen": 0.20,
            "Rohstoffe": 0.10
        }

    # Risiko-Budget als einfacher Skalierungsfaktor (z.B. 0.8 = 80% investiert, 20% Cash)
    scaled = {k: v * risk_budget for k, v in base.items()}
    if risk_budget < 1.0:
        scaled["Geldmarkt"] = scaled.get("Geldmarkt", 0.0) + (1.0 - risk_budget)

    return scaled


def investment_recommendations_v3(risk_budget: float = 1.0):
    """Kombiniert Makro-Trends, Risk Score, Regime, ETF-Mapping und Portfolio-Gewichtung."""
    trends = detect_macro_trends()
    risk = classify_risk_level()
    regime = get_latest_regime()

    weights = portfolio_weights(risk, regime, risk_budget)
    mapping = etf_mapping()

    mapped = {
        asset: mapping.get(asset, [])
        for asset in weights.keys()
    }

    return {
        "macro_trends": trends,
        "risk_level": risk,
        "regime": regime,
        "risk_budget": risk_budget,
        "weights": weights,
        "etf_mapping": mapped
    }


def regime_etf_universe(low, medium, high):
    return {
        "Low Risk": low,
        "Medium Risk": medium,
        "High Risk": high
    }

# ---------------------------------------------------------
# C) PORTFOLIO-OPTIMIERUNG MIT VOLATILITÄTEN (RISK PARITY)
# ---------------------------------------------------------
def risk_parity_weights(returns_df: pd.DataFrame):
    """
    Einfache Risk-Parity-Gewichte:
    - Input: DataFrame mit Spalten = Assets, Zeilen = Renditen
    - Output: dict Asset -> Gewicht
    """
    vol = returns_df.std()
    inv_vol = 1 / vol.replace(0, np.nan)
    weights = inv_vol / inv_vol.sum()
    return weights.to_dict()



def build_regime_risk_parity_portfolio(low, medium, high, period="10y"):
    # 1) Tickerliste bauen
    tickers = list(set(low + medium + high))

    # Debug: Tickerliste anzeigen
    st.write("ETF-Loader – angefragte Ticker:", tickers)

    # 2) Preisdaten laden
    prices = load_etf_prices(tickers, start=None, end=None)

    # Debug: Rohdaten anzeigen
    st.write("ETF-Loader – geladene Daten:", prices.head())

    # 3) Returns berechnen
    rets = prices.pct_change().dropna()

    # 4) Portfolio-Struktur erstellen
    rp_struct = {
        "Low": {"weights": {t: 1/len(low) for t in low}},
        "Medium": {"weights": {t: 1/len(medium) for t in medium}},
        "High": {"weights": {t: 1/len(high) for t in high}},
    }

    # 5) Fehlende Ticker melden
    missing = [t for t in tickers if t not in prices.columns]

    return rp_struct, rets, missing


def hrp_weights(returns_df: pd.DataFrame):
    returns_df = returns_df.dropna(how="all", axis=1)
    if returns_df.shape[1] == 0:
        st.warning("HRP – keine gültigen Spalten in returns_df.")
        return {}

    corr = returns_df.corr().fillna(0.0)
    dist = np.sqrt(0.5 * (1 - corr.clip(-1, 1)))

    try:
        link = linkage(dist, method="single")
    except Exception as e:
        st.error(f"HRP – Fehler beim Clustering: {e}")
        return {}

    sort_ix = leaves_list(link)
    cov = returns_df.cov()
    ordered = cov.iloc[sort_ix, sort_ix]

    def _get_cluster_var(cov_mat, cluster_items):
        sub = cov_mat.loc[cluster_items, cluster_items]
        w = np.ones(len(sub)) / len(sub)
        return float(np.dot(w, np.dot(sub.values, w)))

    def _hrp_alloc(cov_mat, items):
        if len(items) == 1:
            return {items[0]: 1.0}
        split = len(items) // 2
        left = items[:split]
        right = items[split:]

        var_left = _get_cluster_var(cov_mat, left)
        var_right = _get_cluster_var(cov_mat, right)
        alpha_left = 1 - var_left / (var_left + var_right)
        alpha_right = 1 - alpha_left

        w_left = _hrp_alloc(cov_mat, left)
        w_right = _hrp_alloc(cov_mat, right)

        w = {}
        for k, v in w_left.items():
            w[k] = v * alpha_left
        for k, v in w_right.items():
            w[k] = v * alpha_right
        return w

    items = list(ordered.columns)
    w = _hrp_alloc(ordered, items)
    s = sum(w.values()) or 1.0
    return {k: v / s for k, v in w.items()}

    
def build_regime_hrp_portfolio(low, medium, high, rets):
    regime_universe = {
        "Low Risk": low,
        "Medium Risk": medium,
        "High Risk": high,
    }

    result = {}

    for regime, tickers in regime_universe.items():
        valid = [t for t in tickers if t in rets.columns]
        if not valid:
            print(f"WARNUNG HRP: Keine gültigen Ticker im Regime {regime}: {tickers}")
            continue

        sub = rets[valid].dropna(how="all")
        if sub.empty:
            print(f"WARNUNG HRP: Leeres Return-Set im Regime {regime}")
            continue

        w = hrp_weights(sub)
        if not w:
            print(f"WARNUNG HRP: Keine Gewichte im Regime {regime}")
            continue

        result[regime] = {"weights": w, "returns": sub}

    return result


def backtest_regime_hrp(low, medium, high, period="10y", scenario_df=None, scenario_regimes=None):

    all_tickers = sorted({t for lst in [low, medium, high] for t in lst})

    prices, missing = load_etf_prices_monthly(tuple(all_tickers), period=period)

    if prices is None or prices.empty:
        st.error("HRP-Backtest: Keine ETF-Preise geladen.")
        return pd.DataFrame(), {}, missing

    rets = prices.pct_change().dropna()
    if rets.empty:
        st.error("HRP-Backtest: Returns leer.")
        return pd.DataFrame(), {}, missing

    if scenario_regimes is None or scenario_regimes.empty:
        scenario_regimes = detect_risk_regimes().copy()

    scenario_regimes["date"] = pd.to_datetime(scenario_regimes["date"])
    regimes = scenario_regimes.set_index("date").resample("ME").last()

    common_index = rets.index.intersection(regimes.index)
    if len(common_index) == 0:
        st.error("HRP-Backtest: Keine gemeinsamen Monatsenden.")
        return pd.DataFrame(), {}, missing

    rets = rets.loc[common_index]
    regimes = regimes.loc[common_index]

    hrp_struct = build_regime_hrp_portfolio(low, medium, high, rets)

    if not hrp_struct:
        st.error("HRP-Backtest: Keine HRP-Struktur erzeugt.")
        return pd.DataFrame(), {}, missing

    equity = [1.0]
    regime_series = []

    for dt, row in rets.iterrows():
        reg = regimes.loc[dt, "regime"]
        # HIER EINSETZEN
        if scenario_df is not None and dt in scenario_df.index:
            scenario = scenario_df.loc[dt, "scenario"]
        else:
            scenario = None


        regime_series.append(reg)

        if reg not in hrp_struct:
            r = 0.0
        else:
            w = hrp_struct[reg]["weights"]
            r = (row[list(w.keys())] * pd.Series(w)).sum()

        equity.append(equity[-1] * (1 + r))

    df = pd.DataFrame({
        "date": rets.index,
        "equity": equity[1:],
        "regime": regime_series
    })

    return df, hrp_struct, missing


def sharpe_per_regime(equity_df, risk_free_rate=0.0):
    """
    Berechnet Sharpe Ratio pro Regime.
    equity_df: DataFrame mit Spalten ['date', 'equity', 'regime']
    """
    df = equity_df.copy()
    df["ret"] = df["equity"].pct_change()
    df = df.dropna()

    stats = []
    for reg, grp in df.groupby("regime"):
        mean_ret = grp["ret"].mean()
        vol = grp["ret"].std()
        periods_per_year = 12
        ann_ret = (1 + mean_ret) ** periods_per_year - 1
        ann_vol = vol * np.sqrt(periods_per_year)
        sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else np.nan
        stats.append((reg, sharpe))

    return pd.DataFrame(stats, columns=["regime", "sharpe"]).set_index("regime")


def backtest_regime_risk_parity(low, medium, high, period="10y", scenario_df=None, scenario_regimes=None):

    rp_struct, rets, missing = build_regime_risk_parity_portfolio(low, medium, high, period=period)

    if rets is None or rets.empty:
        st.error("Risk-Parity Backtest: Returns leer.")
        return pd.DataFrame(), rp_struct, missing

    if scenario_regimes is None or scenario_regimes.empty:
        scenario_regimes = detect_risk_regimes().copy()

    scenario_regimes = ensure_date_column(scenario_regimes)
    #scenario_regimes["date"] = pd.to_datetime(scenario_regimes["date"])
    regimes = scenario_regimes.set_index("date").resample("ME").last()

    common_index = rets.index.intersection(regimes.index)
    if len(common_index) == 0:
        st.error("Risk-Parity Backtest: Keine gemeinsamen Monatsenden.")
        return pd.DataFrame(), {}, missing

    rets = rets.loc[common_index]
    regimes = regimes.loc[common_index]

    equity = [1.0]
    regime_series = []

    for dt, row in rets.iterrows():
        reg = regimes.loc[dt, "regime"]

        # HIER EINSETZEN
        if scenario_df is not None and dt in scenario_df.index:
            scenario = scenario_df.loc[dt, "scenario"]
        else:
            scenario = None

        regime_series.append(reg)

        if reg not in rp_struct:
            r = 0.0
        else:
            w = rp_struct[reg]["weights"]
            r = (row[list(w.keys())] * pd.Series(w)).sum()

        equity.append(equity[-1] * (1 + r))

    df = pd.DataFrame({
        "date": rets.index,
        "equity": equity[1:],
        "regime": regime_series
    })

    return df, rp_struct, missing


# ---------------------------------------------------------
# D) PORTFOLIO-BACKTESTING (SKELETT)
# ---------------------------------------------------------
def backtest_regime_strategy(scenario_regimes=None):
    """
    Backtest basierend auf historischer Regime-Erkennung.
    Nutzt einfache monatliche Regime-Renditen als Proxy.
    """

    # 1. Regime-Historie laden
    if scenario_regimes is not None and not scenario_regimes.empty:
        regimes = scenario_regimes.copy()
    else:
        regimes = detect_risk_regimes().copy()

    regimes = ensure_date_column(regimes)
    regimes["date"] = pd.to_datetime(regimes["date"])
    regimes = regimes.set_index("date").resample("ME").last()

    # 2. Regime-basierte Renditen
    regime_returns = {
        "Low Risk": 0.012,
        "Medium Risk": 0.004,
        "High Risk": -0.008
    }

    # 3. Equity-Kurve erzeugen
    equity = [1.0]
    equity_curve = []

    for dt, reg in regimes["regime"].items():
        monthly_return = regime_returns.get(reg, 0.0)
        equity.append(equity[-1] * (1 + monthly_return))

        equity_curve.append({
            "date": dt,
            "equity": equity[-1],
            "regime": reg,
            "scenario": None  # dieses Modell hat kein Szenario
        })

    df = pd.DataFrame(equity_curve)
    return df


def backtest_etf_regime_portfolio(ticker_map, period="max", scenario_df=None, scenario_regimes=None):
    """
    Backtest 2.0:
    - ticker_map: dict Regime -> Liste von ETF-Tickern
    - period: Zeitraum für Yahoo Finance (z.B. '10y' oder 'max')
    """
    # 1. Regime-Historie (monatlich)
    if scenario_regimes is not None and not scenario_regimes.empty:
        regimes = scenario_regimes.copy()
    else:
        regimes = detect_risk_regimes().copy()

    # Defensive: sicherstellen, dass 'date' vorhanden ist und gültig
    regimes = ensure_date_column(regimes)
    regimes["date"] = pd.to_datetime(regimes["date"], errors="coerce")
    regimes = regimes.dropna(subset=["date"])
    regimes = regimes.set_index("date").resample("ME").last()

    # 2. Alle ETF-Ticker sammeln
    all_tickers = sorted({t for lst in ticker_map.values() for t in lst})

    # prices: monthly DataFrame (ME index) aus download_etf_history
    prices = download_etf_history(all_tickers, period=period, auto_resample=True)
    if prices is None or prices.empty:
        st.error("ETF-Backtest: Keine ETF-Preise geladen.")
        return pd.DataFrame()

    # ensure datetime index and monthly resample (defensive)
    prices.index = pd.to_datetime(prices.index, errors="coerce")
    prices = prices.sort_index()
    prices = prices.resample("ME").last().ffill().dropna(axis=1, how="all")

    # Monatsrenditen
    rets = prices.pct_change().dropna(how="all")

    # Regimes auf Monatsende bringen (falls noch nicht geschehen)
    regimes.index = pd.to_datetime(regimes.index, errors="coerce")
    regimes = regimes.sort_index()
    regimes = regimes.resample("ME").last()
    

    # gemeinsame Indizes bestimmen und reindexen
    common_index = rets.index.intersection(regimes.index)
    if common_index.empty:
        etf_start, etf_end = rets.index.min(), rets.index.max()
        reg_start, reg_end = regimes.index.min(), regimes.index.max()
        new_start = max(etf_start, reg_start)
        new_end = min(etf_end, reg_end)
        if new_start > new_end:
            st.warning("Keine Überlappung zwischen ETF-Daten und Regimen.")
            return pd.DataFrame()
        rets = rets.loc[new_start:new_end]
        regimes = regimes.loc[new_start:new_end]
        common_index = rets.index.intersection(regimes.index)
        if common_index.empty:
            st.error("Keine gemeinsamen Monatsenden zwischen Returns und Regimen.")
            return pd.DataFrame()

    # final reindex auf gemeinsame Zeitachse
    common_index = common_index.sort_values()
    rets = rets.loc[common_index]
    regimes = regimes.loc[common_index]


    # 5. Backtest durchlaufen
    equity = [1.0]
    regime_series = []
    equity_curve = []

    for dt, row in rets.iterrows():
        reg = regimes.loc[dt, "regime"]

        # Szenario (optional)
        if scenario_df is not None and dt in scenario_df.index:
            scenario = scenario_df.loc[dt, "scenario"]
        else:
            scenario = None

        regime_series.append(reg)

        tickers = ticker_map.get(reg, [])
        if not tickers:
            r = 0.0
            scenario = None
        else:
            w = {t: 1 / len(tickers) for t in tickers}
            if scenario_df is not None and dt in scenario_df.index:
                w = apply_scenario_overlay(w, scenario)
            r = (row[tickers] * pd.Series(w)).sum()

        equity.append(equity[-1] * (1 + r))
        equity_curve.append({"date": dt, "equity": equity[-1], "regime": reg, "scenario": scenario})

    df = pd.DataFrame({
        "date": rets.index,
        "equity": equity[1:],
        "regime": regime_series
    })
    return df
    
        
def performance_stats(equity_df, risk_free_rate=0.0):
    """
    Berechnet einfache Kennzahlen:
    - annualisierte Rendite
    - annualisierte Volatilität
    - Sharpe Ratio
    - Max Drawdown
    """
    df = equity_df.copy().set_index("date")
    df["ret"] = df["equity"].pct_change()
    df = df.dropna()

    mean_ret = df["ret"].mean()
    vol = df["ret"].std()
    periods_per_year = 12  # Monatsdaten

    ann_ret = (1 + mean_ret) ** periods_per_year - 1
    ann_vol = vol * np.sqrt(periods_per_year)
    sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else np.nan

    # Max Drawdown
    cum_max = df["equity"].cummax()
    drawdown = df["equity"] / cum_max - 1
    max_dd = drawdown.min()

    return {
        "annual_return": ann_ret,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd
    }


def regime_heatmap_data(equity_df):
    """
    Liefert durchschnittliche Monatsrenditen pro Regime für Heatmap.
    """
    df = equity_df.copy()
    df["ret"] = df["equity"].pct_change()
    df = df.dropna()
    return df.groupby("regime")["ret"].mean().to_frame("avg_monthly_return")


def regime_transition_matrix(period="max"):
    """
    Erstellt eine Regime-Transitionsmatrix basierend auf monatlichen Regimen.
    """

    # 1. Regime-Historie laden
    regimes = detect_risk_regimes().copy()
    regimes = ensure_date_column(regimes)
    regimes["date"] = pd.to_datetime(regimes["date"])
    regimes = regimes.set_index("date").resample("ME").last()

    # 2. ETF-Preise laden (für spätere Erweiterungen)
    #    → wichtig, damit 'prices' existiert
    all_tickers = ["CSPX.L", "EQQQ.L", "EUNL.DE", "IQQ0.DE", "IMEU.L", "AGGG.L", "IEGA.L", "SGLN.L"]
    prices = download_etf_history(all_tickers, period=period)
    prices = prices.resample("ME").last().ffill()

    # 3. Regime-Liste extrahieren
    reg_series = regimes["regime"]

    # 4. Transitionen zählen
    transitions = pd.crosstab(
        reg_series.shift(1),
        reg_series,
        normalize="index"
    )

    return transitions


def generate_investment_package(regime, scenario, risk_score, etf_universes):
    key = map_regime_to_key(regime)
    etf_weights = etf_universes.get(key, {})

    equity_pkg = select_equity_package(regime, scenario, risk_score)

    return {
        "ETF": etf_weights,
        "Equity Package": equity_pkg,
        "Hedge": "Gold + Commodities",
        "Risk Budget": 0.4
    }
