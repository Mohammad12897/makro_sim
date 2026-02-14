#core/backend/ki_score.py

import numpy as np
import pandas as pd

def normalize(value, min_val, max_val):
    if max_val - min_val == 0:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def compute_ki_score(price_series: pd.Series, return_factors=False):
    """
    Berechnet einen KI-Score (0–100) aus einer Preiszeitreihe.
    Wenn return_factors=True, werden zusätzlich die normierten Faktoren zurückgegeben.
    """

    # 1. Renditen
    returns = price_series.pct_change().dropna()

    # 2. Momentum (letzte 90 Tage)
    momentum = price_series.iloc[-1] / price_series.iloc[-90] - 1
    momentum_norm = normalize(momentum, -0.2, 0.3)

    # 3. Volatilität
    vol = returns.std()
    vol_norm = normalize(vol, 0.005, 0.05)

    # 4. Sharpe Ratio
    sharpe = returns.mean() / (returns.std() + 1e-9)
    sharpe_norm = normalize(sharpe, -1, 2)

    # 5. Max Drawdown
    roll_max = price_series.cummax()
    drawdown = ((price_series - roll_max) / roll_max).min()
    drawdown_norm = normalize(abs(drawdown), 0, 0.5)

    # 6. Trendstabilität (R²)
    x = np.arange(len(price_series))
    y = price_series.values
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2)
    trend_stability_norm = normalize(r2, 0, 1)

    # 7. KI-Score
    score = (
        0.25 * momentum_norm +
        0.20 * sharpe_norm +
        0.20 * trend_stability_norm +
        0.20 * (1 - drawdown_norm) +
        0.15 * (1 - vol_norm)
    ) * 100

    score = float(np.clip(score, 0, 100))

    if return_factors:
        return score, {
            "momentum": momentum_norm,
            "volatility": vol_norm,
            "drawdown": drawdown_norm,
            "sharpe": sharpe_norm,
            "trend_stability": trend_stability_norm
        }

    return score

def explain_ki_score(ticker, score, factors):
    """
    Erzeugt eine ausführliche, verständliche Erklärung für den KI‑Score eines Assets.
    'factors' enthält normierte Werte (0–1):
        momentum, volatility, drawdown, sharpe, trend_stability
    """

    # Alle Werte sicher in float umwandeln
    momentum = float(factors["momentum"])
    volatility = float(factors["volatility"])
    drawdown = float(factors["drawdown"])
    sharpe = float(factors["sharpe"])
    stability = float(factors["trend_stability"])

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
- **Trendqualität:** {'stabil' if stability > 0.6 else 'durchwachsen' if stability > 0.3 else 'instabil'}

Der KI‑Score kombiniert alle Faktoren zu einer Gesamtbewertung:

- **80–100:** Sehr starke Muster, attraktives Risiko‑Profil  
- **60–80:** Gute Qualität, solide Entwicklung  
- **40–60:** Neutral, ausgewogen  
- **20–40:** Schwach, erhöhte Risiken  
- **0–20:** Sehr instabil, hohe Verlustgefahr  

---

## 📝 Fazit für {ticker}

Zusammengefasst zeigt **{ticker}**, dass es aktuell **{summary}**.  
Diese Einschätzung basiert auf Trendstärke, Risiko, Stabilität und Renditequalität.
"""
