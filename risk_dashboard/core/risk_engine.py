#core/risk_engine.py

def compute_risk_scores(presets):
    # Slider-Werte sind bereits 0–1, wir verwenden sie direkt
    return presets


def apply_shocks_to_scores(base_scores, shock_values):
    """
    Wendet Szenario-Shocks auf Risiko-Scores an.
    Floats werden geschockt, Dicts unverändert übernommen.
    """

    new_scores = {}

    for key, value in base_scores.items():
        if isinstance(value, (int, float)):
            shock = shock_values.get(key, 0.0)
            new_scores[key] = max(0.0, min(1.0, value + shock))
        elif isinstance(value, dict):
            new_scores[key] = value
        else:
            new_scores[key] = value

    return new_scores
