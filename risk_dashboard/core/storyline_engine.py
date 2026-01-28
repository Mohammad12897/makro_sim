# core/storyline_engine.py

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


def generate_executive_summary(indicators: dict, ampel_text: str) -> str:
    high = [k for k, v in indicators.items() if v > 0.4]
    medium = [k for k, v in indicators.items() if 0.2 < v <= 0.4]
    low = [k for k, v in indicators.items() if v <= 0.2]

    lines = [f"Gesamtrisiko: {ampel_text}.", ""]

    if high:
        lines.append(f"• Hohe Risiken bei: {', '.join(high)}.")
    if medium:
        lines.append(f"• Moderate Risiken bei: {', '.join(medium)}.")
    if low:
        lines.append(f"• Stabile oder geringe Risiken bei: {', '.join(low)}.")

    lines.append("")
    lines.append("Die Gesamtlage zeigt ein sensibles, aber strukturiert einschätzbares Risikoprofil.")

    return "\n".join(lines)


def interpret_indicator(name: str, value: float) -> str:
    if value > 0.4:
        return f"{name} verschlechtert sich deutlich und erhöht das Gesamtrisiko spürbar."
    elif value > 0.2:
        return f"{name} ist moderat erhöht und wirkt leicht belastend."
    elif value < -0.2:
        return f"{name} verbessert sich klar und wirkt stabilisierend."
    else:
        return f"{name} bleibt weitgehend stabil und neutral."


def generate_storyline(indicators: dict) -> str:
    parts = [interpret_indicator(k, v) for k, v in indicators.items()]
    text = " ".join(parts)
    return f"Die Indikatoren zeichnen folgendes Bild: {text}"
