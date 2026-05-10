#core/country/country_storyline.py

def generate_country_storyline(df):
    best = df.loc[df["Rendite"].idxmax()]
    safest = df.loc[df["VolatilitÃ¤t"].idxmin()]
    worst_dd = df.loc[df["Max Drawdown"].idxmin()]

    text = (
        f"{best['Land/Index']} zeigt die hÃ¶chste Rendite im Vergleich. "
        f"{safest['Land/Index']} weist die geringste VolatilitÃ¤t auf und gilt damit als stabilstes Land. "
        f"{worst_dd['Land/Index']} hat den tiefsten Drawdown und reagiert am stÃ¤rksten auf Stressphasen."
    )

    return text

