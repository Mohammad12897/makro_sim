# risk_dashboard/core/asset_packages.py
import typing as t

# Beispielpakete: Key = Ticker oder Strategie, Value = Gewicht (soll auf 1.0 normiert sein)
equity_package_high_risk = {
    "AAPL": 0.20,
    "MSFT": 0.18,
    "NVDA": 0.15,
    "AMZN": 0.12,
    "SMALL_CAP_GROWTH": 0.35
}

equity_package_medium_risk = {
    "CSPX.L": 0.30,
    "IEFA": 0.25,
    "VWO": 0.15,
    "VALUE_ETF": 0.20,
    "DIVIDEND_ETF": 0.10
}

equity_package_low_risk = {
    "BND": 0.40,
    "CASH_EQUIV": 0.30,
    "DEFENSIVE_EQT": 0.30
}

# Optional: Hilfsfunktion zur Normalisierung
def normalize_weights(d):
    total = sum(d.values()) or 1.0
    return {k: v / total for k, v in d.items()}


def select_equity_package(regime, scenario, risk_score):
    """
    Einfache Regelbasis:
    - regime: z.B. 'High', 'Medium', 'Low' oder Labels aus map_regime_to_label
    - scenario: z.B. 'Stagflation', 'Growth', ...
    - risk_score: numerischer Wert 0..1
    Rückgabe: normalisiertes dict mit Gewichten
    """
    if regime is None:
        return normalize_weights(equity_package_medium_risk)

    label = str(regime).lower()
    if "high" in label:
        base = equity_package_high_risk
    elif "low" in label:
        base = equity_package_low_risk
    else:
        base = equity_package_medium_risk

    # Beispiel: Szenario‑Adjustment (kleinere Modifikation)
    if scenario and "stag" in str(scenario).lower():
        adj = {k: v * 0.9 for k, v in base.items()}
        adj["COMMODITIES"] = adj.get("COMMODITIES", 0) + 0.1
        return normalize_weights(adj)

    # Beispiel: Risiko‑Score Adjustment (mehr Cash bei hohem Risiko)
    if risk_score is not None and risk_score > 0.7:
        adj = dict(base)
        adj["CASH_EQUIV"] = adj.get("CASH_EQUIV", 0) + 0.15
        return normalize_weights(adj)

    return normalize_weights(base)


def normalize_weights(d):
    total = sum(d.values()) or 1.0
    return {k: v / total for k, v in d.items()}

def parse_etf_input(defaults, extra_csv):
    extras = [t.strip().upper() for t in (extra_csv or "").split(",") if t.strip()]
    tickers = list(dict.fromkeys(defaults + extras))
    if not tickers:
        return {}
    w = 1.0 / len(tickers)
    return normalize_weights({t: w for t in tickers})

def map_regime_to_key(regime):
    r = str(regime).lower()
    if "low" in r:
        return "low"
    if "high" in r:
        return "high"
    return "medium"


def select_equity_package(regime, scenario, risk_score):
    # Beispiel – du kannst es später verfeinern
    key = map_regime_to_key(regime)
    if key == "high":
        return {"QQQ": 0.5, "NVDA": 0.5}
    if key == "low":
        return {"BND": 0.5, "GLD": 0.5}
    return {"CSPX.L": 0.5, "IMEU.L": 0.5}
