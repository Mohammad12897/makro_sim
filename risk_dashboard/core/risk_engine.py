# risk_dashboard/core/risk_engine.py
import pandas as pd
import numpy as np
from risk_dashboard.core.macro_loader import load_macro_series
from scipy.stats import zscore
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------
# 1) Normalisierung
# ---------------------------------------------------------

def _normalize_series(s: pd.Series) -> pd.Series:
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty or s.max() == s.min():
        return pd.Series(0.5, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


# ---------------------------------------------------------
# 2) Risiko-Score
# ---------------------------------------------------------


# ---------------------------------------------------------
# 3) Szenario-Framework
# ---------------------------------------------------------

def classify_scenario_from_score(score):
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

def build_scenario_series(risk_score_df):
    df = risk_score_df.copy()

    # Unterstützt beide Versionen
    score_col = "risk_score_pca" if "risk_score_pca" in df.columns else "risk_score"

    df["scenario"] = df[score_col].apply(classify_scenario_from_score)
    return df


def build_fx_risk_factors(fx_prices):
    df = fx_prices.copy()

    # Spaltenname automatisch erkennen
    col = df.columns[0]   # z.B. "DX-Y.NYB"

    df["usd_trend"] = df[col].pct_change(60)
    df["fx_vol"] = df[col].pct_change().rolling(60).std()

    return df


def build_market_risk_factors(etf_prices: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(index=etf_prices.index)

    # Momentum (z. B. SPY 60‑Tage)
    df["equity_momentum"] = etf_prices["SPY"].pct_change(60)

    # Volatilität (20‑Tage)
    df["equity_vol"] = etf_prices["SPY"].pct_change().rolling(20).std()

    return df.dropna()



def load_risk_factors():
    gdp = load_macro_series("GDP")
    cpi = load_macro_series("CPIAUCSL")
    unrate = load_macro_series("UNRATE")
    fedfunds = load_macro_series("FEDFUNDS")
    indpro = load_macro_series("INDPRO")

    df = gdp.merge(cpi, on="date", suffixes=("_gdp", "_cpi"))
    df = df.merge(unrate, on="date")
    df = df.merge(fedfunds, on="date", suffixes=("", "_fed"))
    df = df.merge(indpro, on="date", suffixes=("", "_ind"))

    df.columns = ["date", "gdp", "cpi", "unrate", "fedfunds", "indpro"]
    return df



def compute_raw_risk_score():
    """
    Beispiel‑Skeleton: berechnet einen rohen Risiko‑Score und gibt ein DataFrame zurück.
    Ersetze die Dummy‑Logik durch deine echte Feature‑Extraktion / PCA / Modell.
    """
    # Beispiel: Erzeuge Dummy‑Zeitreihe (ersetzen durch echte Daten)
    dates = pd.date_range("2020-01-01", periods=24, freq="Q")
    raw_scores = np.random.normal(loc=0.0, scale=1.0, size=len(dates))

    df = pd.DataFrame({"risk_score_pca": raw_scores}, index=dates)
    return df



def compute_risk_score_v2(normalize=True, method="minmax"):
    """
    Berechnet den Risiko-Score und liefert ein DataFrame mit Spalte 'risk_score'.
    normalize: bool, ob auf [0,1] normiert werden soll
    method: "minmax" oder "sigmoid"
    """
    # 1) Rohscore berechnen (ersetze durch deine Implementierung)
    df = compute_raw_risk_score()  # muss ein DataFrame liefern

    # 2) Spaltenname vereinheitlichen
    if "risk_score_pca" in df.columns and "risk_score" not in df.columns:
        df = df.rename(columns={"risk_score_pca": "risk_score"})

    # 3) DatetimeIndex sicherstellen
    if not isinstance(df.index, pd.DatetimeIndex) and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date")

    # 4) Normierung (optional)
    if normalize and "risk_score" in df.columns:
        rs = df["risk_score"].astype(float)
        if method == "minmax":
            if rs.max() != rs.min():
                df["risk_score"] = (rs - rs.min()) / (rs.max() - rs.min())
            else:
                df["risk_score"] = 0.5
        elif method == "sigmoid":
            df["risk_score"] = 1 / (1 + np.exp(-rs))
        else:
            if rs.max() != rs.min():
                df["risk_score"] = (rs - rs.min()) / (rs.max() - rs.min())
            else:
                df["risk_score"] = 0.5

    # 5) fehlende Scores entfernen
    df = df.dropna(subset=["risk_score"])

    return df


def compute_pca_details():
    df = load_risk_factors()
    df = df.ffill().bfill()

    factors = df[["gdp", "cpi", "unrate", "fedfunds", "indpro"]]
    factors_z = factors.apply(zscore)

    pca = PCA(n_components=5)
    pca.fit(factors_z)

    explained = pca.explained_variance_ratio_
    loadings = pd.DataFrame(
        pca.components_.T,
        columns=[f"PC{i+1}" for i in range(5)],
        index=factors.columns
    )

    return explained, loadings


def detect_risk_regimes():
    """
    Ermittelt Regime via KMeans auf der vorhandenen Risiko-Score-Spalte.
    Liefert das DataFrame mit zusätzlichen Spalten 'regime' (int) und 'regime_label' (str).
    """
    df = compute_risk_score_v2(normalize=True, method="minmax")

    # Defensive Prüfung
    if df is None or df.empty:
        raise ValueError("Keine Risiko-Daten vorhanden in detect_risk_regimes().")

    # Priorisierte Score-Spalten (Fallbacks)
    preferred_cols = ["risk_score", "risk_score_pca", "raw_score"]
    score_col = next((c for c in preferred_cols if c in df.columns), None)
    if score_col is None:
        raise KeyError(f"Keine Score-Spalte gefunden. Vorhandene Spalten: {df.columns.tolist()}")

    # Sicherstellen, dass die Spalte numerisch ist
    df = df.copy()
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df = df.dropna(subset=[score_col])
    if df.empty:
        raise ValueError("Nach Konvertierung/DropNa ist kein Score mehr vorhanden.")

    # KMeans clustering
    kmeans = KMeans(n_clusters=3, n_init="auto", random_state=0)
    df["regime"] = kmeans.fit_predict(df[[score_col]])

    # Clusterzentren sortieren und in Low/Medium/High umbenennen
    centers = kmeans.cluster_centers_.flatten()
    order = np.argsort(centers)  # index der Zentren von klein nach groß

    label_map = {
        order[0]: "Low Risk",
        order[1]: "Medium Risk",
        order[2]: "High Risk"
    }

    df["regime_label"] = df["regime"].map(label_map)

    # Optional: Index/Datum sicherstellen (falls downstream benötigt)
    if not isinstance(df.index, pd.DatetimeIndex) and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date")

    return df


def compute_pca_score(df):
    """
    Berechnet den PCA-basierten Makro-Risiko-Score.
    Erwartet Spalten: GDP, CPI, UNRATE, FEDFUNDS.
    Gibt eine Serie mit dem PCA-Score zurück.
    """

    macro_vars = ["GDP", "CPI", "UNRATE", "FEDFUNDS"]

    # Sicherstellen, dass alle Variablen vorhanden sind
    for v in macro_vars:
        if v not in df.columns:
            raise ValueError(f"Variable {v} fehlt in DataFrame")

    # Daten extrahieren
    X = df[macro_vars].copy()

    # Skalieren
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA
    pca = PCA(n_components=1)
    score = pca.fit_transform(X_scaled).flatten()

    return pd.Series(score, index=df.index, name="risk_score_pca")

def assign_regime(score_series):
    """
    Ordnet jedem PCA-Score ein Regime zu:
    Low Risk, Medium Risk, High Risk.
    Schwellenwerte basieren auf Quantilen.
    """

    q33 = score_series.quantile(0.33)
    q66 = score_series.quantile(0.66)

    def classify(x):
        if x <= q33:
            return "Low Risk"
        elif x <= q66:
            return "Medium Risk"
        else:
            return "High Risk"

    return score_series.apply(classify)

def detect_risk_regimes_from_scenario(scenario_df):
    df = scenario_df.copy()
    df["risk_score_pca"] = compute_pca_score(df)
    df["regime_label"] = assign_regime(df["risk_score_pca"])
    return df
