#core/backend/ki_score.py

import numpy as np
import pandas as pd

def normalize(value, min_val, max_val):
    # Series → float
    if isinstance(value, pd.Series):
        value = float(value.iloc[0])

    # NaN → 0
    if value is None or np.isnan(value):
        return 0.0

    # Division durch 0 vermeiden
    if max_val - min_val == 0:
        return 0.5

    # Normierung
    norm = (value - min_val) / (max_val - min_val)

    # Clipping auf 0–1
    return max(0.0, min(1.0, float(norm)))
    
def to_float(x):
    """Konvertiert Series oder numpy-Werte sicher in float."""
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)


def compute_ki_score(price_series: pd.Series, return_factors=False):
    """
    Berechnet einen KI-Score (0–100) aus einer Preiszeitreihe.
    Wenn return_factors=True, werden zusätzlich die normierten Faktoren zurückgegeben.
    """

    # Sicherheitscheck: mindestens 120 Datenpunkte
    if len(price_series) < 120:
        return 0 if not return_factors else (0, {
            "momentum": 0,
            "volatility": 0,
            "drawdown": 0,
            "sharpe": 0,
            "trend_stability": 0
        })

    # 1. Renditen
    returns = price_series.pct_change().dropna()

    # 2. Momentum (letzte 90 Tage)
    try:
        momentum = price_series.iloc[-1] / price_series.iloc[-90] - 1
    except Exception:
        momentum = 0
    momentum_norm = normalize(to_float(momentum), -0.2, 0.3)

    # 3. Volatilität
    vol = to_float(returns.std())
    vol_norm = normalize(vol, 0.005, 0.05)

    # 4. Sharpe Ratio
    sharpe = to_float(returns.mean()) / (to_float(returns.std()) + 1e-9)
    sharpe_norm = normalize(sharpe, -1, 2)

    # 5. Max Drawdown
    roll_max = price_series.cummax()
    drawdown = to_float(((price_series - roll_max) / roll_max).min())
    drawdown_norm = normalize(abs(drawdown), 0, 0.5)

    # 6. Trendstabilität (R²)
    x = np.arange(len(price_series))
    y = price_series.values
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2)
    trend_stability_norm = normalize(to_float(r2), 0, 1)

    # 7. KI-Score (robust)
    score = (
        to_float(momentum_norm) * 25 +
        (1 - to_float(vol_norm)) * 20 +
        (1 - to_float(drawdown_norm)) * 20 +
        to_float(sharpe_norm) * 20 +
        to_float(trend_stability_norm) * 15
    )

    score = max(0, min(100, float(score)))

    if return_factors:
        return score, {
            "momentum": float(momentum_norm),
            "volatility": float(vol_norm),
            "drawdown": float(drawdown_norm),
            "sharpe": float(sharpe_norm),
            "trend_stability": float(trend_stability_norm)
        }

    return score

def explain_ki_score(ticker, score, factors):
    """
    Erzeugt eine ausführliche, verständliche Erklärung für den KI‑Score eines Assets.
    'factors' enthält normierte Werte (0–1):
        momentum, volatility, drawdown, sharpe, trend_stability
    """

    # Alle Werte sicher in float umwandeln
    momentum = to_float(factors["momentum"])
    volatility = to_float(factors["volatility"])
    drawdown = to_float(factors["drawdown"])
    sharpe = to_float(factors["sharpe"])
    stability = to_float(factors["trend_stability"])

    # Ampel-Logik
    def amp(value):
        if value >= 0.66:
            return "🟢"
        elif value >= 0.33:
            return "🟡"
        else:
            return "🔴"

    # Risiko-Profil
    risiko_level = (
        "niedrig" if volatility < 0.3 else
        "mittel" if volatility < 0.6 else
        "hoch"
    )

    # Trend-Profil
    trend_level = (
        "stark" if momentum > 0.6 else
        "neutral" if momentum > 0.3 else
        "schwach"
    )

    # Sharpe-Interpretation
    sharpe_level = (
        "sehr gut" if sharpe > 0.66 else
        "solide" if sharpe > 0.33 else
        "schwach"
    )

    # Gesamtbewertung
    if score >= 80:
        summary = "ein sehr starkes Muster zeigt"
    elif score >= 60:
        summary = "eine solide Entwicklung aufweist"
    elif score >= 40:
        summary = "aktuell neutral wirkt"
    elif score >= 20:
        summary = "deutliche Schwächen zeigt"
    else:
        summary = "ein sehr hohes Risiko aufweist"

    # Stärken/Schwächen
    strengths = []
    weaknesses = []

    if momentum > 0.5:
        strengths.append("positives Momentum")
    else:
        weaknesses.append("schwaches Momentum")

    if volatility < 0.4:
        strengths.append("günstiges Risiko‑Profil")
    else:
        weaknesses.append("erhöhte Volatilität")

    if sharpe > 0.5:
        strengths.append("gute Risiko‑Rendite‑Relation")
    else:
        weaknesses.append("schwache Sharpe‑Ratio")

    if stability > 0.5:
        strengths.append("stabiler Trend")
    else:
        weaknesses.append("instabiler Trendverlauf")

    strengths_text = ", ".join(strengths) if strengths else "keine ausgeprägten Stärken"
    weaknesses_text = ", ".join(weaknesses) if weaknesses else "keine wesentlichen Schwächen"

    return f"""
### 📊 KI‑Score Analyse für **{ticker}**

Der KI‑Score von **{ticker}** beträgt **{score:.1f} / 100**.  
Er basiert auf einer kombinierten Analyse von Trend, Risiko, Stabilität und Renditequalität.

---

## 🔍 Einzel‑Faktoren (mit Ampel‑Bewertung)

**Momentum:** {momentum:.2f} {amp(momentum)}  
→ Stärke des kurzfristigen Trends.

**Volatilität:** {volatility:.2f} {amp(1 - volatility)}  
→ Schwankungsintensität (je niedriger, desto besser).

**Drawdown:** {drawdown:.2f} {amp(1 - drawdown)}  
→ Rückschlagsrisiko der letzten Monate.

**Sharpe Ratio:** {sharpe:.2f} {amp(sharpe)}  
→ Risiko‑angepasste Renditequalität.

**Trendstabilität:** {stability:.2f} {amp(stability)}  
→ Wie sauber und konsistent der Trend verläuft.

---

## 🧠 Gesamtinterpretation

- **Momentum:** {trend_level}  
- **Risiko:** {risiko_level}  
- **Sharpe‑Profil:** {sharpe_level}  
- **Trendqualität:** {'stabil' if stability > 0.6 else 'durchwachsen' if stability > 0.3 else 'instabil'}

---

## 💡 Stärken & Schwächen

**Stärken:**  
- {strengths_text}

**Schwächen:**  
- {weaknesses_text}

---

## 📝 Fazit für {ticker}

Zusammengefasst zeigt **{ticker}**, dass es aktuell **{summary}**.  
Diese Einschätzung basiert auf Trendstärke, Risiko, Stabilität und Renditequalität.
"""
