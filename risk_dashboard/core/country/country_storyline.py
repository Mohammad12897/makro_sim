#core/country/country_storyline.py

def generate_country_storyline(df):
    best = df.loc[df["Rendite"].idxmax()]
    safest = df.loc[df["Volatilität"].idxmin()]
    worst_dd = df.loc[df["Max Drawdown"].idxmin()]

    text = (
        f"{best['Land/Index']} zeigt die höchste Rendite im Vergleich. "
        f"{safest['Land/Index']} weist die geringste Volatilität auf und gilt damit als stabilstes Land. "
        f"{worst_dd['Land/Index']} hat den tiefsten Drawdown und reagiert am stärksten auf Stressphasen."
    )

    return text
