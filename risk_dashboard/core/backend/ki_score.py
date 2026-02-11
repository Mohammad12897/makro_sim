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
    Erzeugt eine verständliche Erklärung für den KI‑Score eines Assets.
    'factors' ist ein Dict mit normierten Werten (0–1):
        momentum, volatility, drawdown, sharpe, trend_stability
    """

    momentum = factors["momentum"]
    volatility = factors["volatility"]
    drawdown = factors["drawdown"]
    sharpe = factors["sharpe"]
    stability = factors["trend_stability"]

    return f"""
### 📊 KI‑Score Erklärung für **{ticker}**

Der KI‑Score von **{ticker}** beträgt **{score:.1f} / 100**.  
Er basiert auf einer kombinierten Analyse der letzten Monate und bewertet die Musterqualität des Assets.

---

## 🔍 Einzel‑Faktoren

**Momentum:** {momentum:.2f}  
→ Wie stark der Trend zuletzt war.  
- Hoher Wert = starkes Aufwärtsmomentum  
- Niedriger Wert = schwacher oder negativer Trend  

**Volatilität:** {volatility:.2f}  
→ Wie stark das Asset schwankt.  
- Hoher Wert = riskant  
- Niedriger Wert = stabil  

**Drawdown:** {drawdown:.2f}  
→ Wie tief das Asset zuletzt gefallen ist.  
- Hoher Wert = starke Rückschläge  
- Niedriger Wert = geringe Verluste  

**Sharpe Ratio:** {sharpe:.2f}  
→ Risiko‑angepasste Rendite.  
- Hoher Wert = gute Rendite bei geringem Risiko  
- Niedriger Wert = schlechte Risiko‑Rendite‑Relation  

**Trendstabilität:** {stability:.2f}  
→ Wie „ruhig“ und konsistent der Trend ist.  
- Hoher Wert = sauberer Trend  
- Niedriger Wert = chaotische Bewegungen  

---

## 🧠 Gesamtinterpretation

Der KI‑Score kombiniert alle Faktoren zu einer einzigen Kennzahl:

- **80–100:** Sehr starke Muster, attraktives Risiko‑Profil  
- **60–80:** Gute Qualität, solide Entwicklung  
- **40–60:** Neutral, weder besonders stark noch schwach  
- **20–40:** Schwache Muster, erhöhte Risiken  
- **0–20:** Chaotisch, instabil, hohe Verlustgefahr  

---

## 📝 Fazit für {ticker}

Basierend auf den Faktoren zeigt **{ticker}**:

- Momentum: {'hoch' if momentum > 0.6 else 'mittel' if momentum > 0.3 else 'schwach'}  
- Risiko: {'niedrig' if volatility < 0.3 else 'mittel' if volatility < 0.6 else 'hoch'}  
- Trendqualität: {'stabil' if stability > 0.6 else 'durchwachsen' if stability > 0.3 else 'instabil'}  

**Gesamtbewertung:**  
→ Der KI‑Score von **{score:.1f}** zeigt, dass {ticker} aktuell **{
    'ein sehr starkes Muster hat' if score >= 80 else
    'eine solide Entwicklung zeigt' if score >= 60 else
    'neutral wirkt' if score >= 40 else
    'Schwächen aufweist' if score >= 20 else
    'sehr riskant erscheint'
}**.
"""
