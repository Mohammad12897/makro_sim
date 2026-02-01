#core/analysis/visualization/lexicon.py

def get_lexicon(tab_type: str):
    """
    Liefert ein tab-spezifisches Lexikon als Liste von Dicts.
    tab_type: "aktien", "laender", "portfolio"
    """

    base = [
        {"Kennzahl": "1Y %", "Erklärung": "Performance der letzten 12 Monate"},
        {"Kennzahl": "5Y %", "Erklärung": "Performance der letzten 5 Jahre"},
        {"Kennzahl": "Volatilität %", "Erklärung": "Schwankungsbreite der Renditen"},
        {"Kennzahl": "Sharpe", "Erklärung": "Rendite pro Risikoeinheit"},
        {"Kennzahl": "Max Drawdown %", "Erklärung": "Größter historischer Verlust"},
        {"Kennzahl": "Beta", "Erklärung": "Sensitivität gegenüber dem Markt"},
    ]

    if tab_type == "aktien":
        extra = [
            {"Kennzahl": "KGV", "Erklärung": "Kurs-Gewinn-Verhältnis"},
            {"Kennzahl": "KUV", "Erklärung": "Kurs-Umsatz-Verhältnis"},
        ]
        return base + extra

    if tab_type == "laender":
        extra = [
            {"Kennzahl": "BIP-Wachstum", "Erklärung": "Wirtschaftswachstum des Landes"},
            {"Kennzahl": "Inflation", "Erklärung": "Teuerungsrate"},
        ]
        return base + extra

    if tab_type == "portfolio":
        extra = [
            {"Kennzahl": "Gewichteter Sharpe", "Erklärung": "Sharpe des Gesamtportfolios"},
            {"Kennzahl": "Gewichtete Volatilität", "Erklärung": "Risiko des Gesamtportfolios"},
        ]
        return base + extra

    return base
