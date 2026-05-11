#core/portfolio/portfolio_storyline.py

def generate_portfolio_storyline(weights, stats):
    lines = []

    # Gewichtung interpretieren
    high = [a for a, w in weights.items() if w > 0.4]
    medium = [a for a, w in weights.items() if 0.2 < w <= 0.4]
    low = [a for a, w in weights.items() if w <= 0.2]

    if high:
        lines.append(f"Das Portfolio ist stark fokussiert auf: {', '.join(high)}.")
    if medium:
        lines.append(f"Moderate Allokationen bestehen in: {', '.join(medium)}.")
    if low:
        lines.append(f"Kleine Beimischungen finden sich in: {', '.join(low)}.")

    # Risiko interpretieren
    vol = stats["Volatilität"]
    dd = stats["Max Drawdown"]

    if vol > 0.25:
        lines.append("Die Volatilität ist hoch, was auf ein risikoreiches Portfolio hindeutet.")
    elif vol > 0.15:
        lines.append("Die Volatilität ist moderat und gut kontrollierbar.")
    else:
        lines.append("Die Volatilität ist niedrig – das Portfolio ist defensiv ausgerichtet.")

    if dd < -0.3:
        lines.append("Der maximale Drawdown ist tief – starke Verluste in Stressphasen.")
    elif dd < -0.15:
        lines.append("Der Drawdown ist moderat – gewisse Krisenanfälligkeit.")
    else:
        lines.append("Der Drawdown ist gering – gute Stabilität in Stressphasen.")

    return " ".join(lines)
