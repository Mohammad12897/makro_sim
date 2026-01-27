# core/storyline_engine.py

# ---------------------------------------------------------
# Hilfsfunktion: schöne Namen für Dimensionen
# ---------------------------------------------------------

def interpret_indicator(name, value):
    if value > 0.4:
        return f"• {name}: deutlich erhöht → Risiko steigt"
    elif value > 0.2:
        return f"• {name}: moderat erhöht → leichte Belastung"
    elif value < -0.2:
        return f"• {name}: deutlich rückläufig → Entspannung"
    else:
        return f"• {name}: stabil"

def generate_storyline(indicators: dict):
    lines = [interpret_indicator(k, v) for k, v in indicators.items()]
    summary = "\n".join(lines)
    return f"### Risiko‑Storyline\n\n{summary}"
