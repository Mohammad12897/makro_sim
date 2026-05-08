# core/risk_ampel.py
def compute_risk_score(indicators: dict):
    vals = [abs(v) for v in indicators.values()]
    return sum(vals) / len(vals)

def risk_color(score):
    if score < 0.25:
        return "🟢 Geringes Risiko"
    elif score < 0.5:
        return "🟡 Mittleres Risiko"
    else:
        return "🔴 Hohes Risiko"
