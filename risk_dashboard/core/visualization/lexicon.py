#core/visualization/lexicon.py


def get_lexicon(tab_type: str, mode: str = "einsteiger"):
    """
    Liefert ein tab-spezifisches Lexikon als Liste von Dicts.
    mode: "einsteiger" oder "experte"
    """

    def e(ein, exp):
        return exp if mode == "experte" else ein

    lex = [
        {
            "Kennzahl": "Radar Aktien",
            "Erklärung": e(
                "Zeigt Stärken und Schwächen einer Aktie in den Bereichen Performance, Risiko, Bewertung und Makro-Umfeld.",
                "Visualisiert die Aktie entlang von Performance-, Risiko-, Bewertungs- und Makro-Dimensionen, normiert auf 0–1 zur direkten Vergleichbarkeit."
            ),
        },
        {"Kennzahl": "1Y %", "Erklärung": e(
            "Rendite der letzten 12 Monate.",
            "Total Return der letzten ca. 252 Handelstage."
        )},
        {"Kennzahl": "5Y %", "Erklärung": e(
            "Rendite der letzten 5 Jahre.",
            "Annualisierte Rendite über 5 Jahre."
        )},
        {"Kennzahl": "Volatilität %", "Erklärung": e(
            "Wie stark die Aktie schwankt.",
            "Standardabweichung der täglichen Renditen (historische Volatilität)."
        )},
        {"Kennzahl": "Sharpe", "Erklärung": e(
            "Rendite pro Risikoeinheit.",
            "Sharpe Ratio = (Portfoliorendite − risikofreier Zins) / Volatilität."
        )},
        {"Kennzahl": "Max Drawdown %", "Erklärung": e(
            "Größter historischer Verlust vom Hoch zum Tief.",
            "Maximaler kumulierter Verlust relativ zum vorherigen Höchststand."
        )},
        {"Kennzahl": "Beta", "Erklärung": e(
            "Wie stark die Aktie dem Markt folgt.",
            "Kovarianz(Aktie, Markt) / Varianz(Markt); Maß für systematisches Risiko."
        )},
        {"Kennzahl": "KGV", "Erklärung": e(
            "Kurs-Gewinn-Verhältnis: Preis im Verhältnis zum Gewinn.",
            "Price/Earnings: Marktkapitalisierung geteilt durch Jahresüberschuss."
        )},
        {"Kennzahl": "KUV", "Erklärung": e(
            "Kurs-Umsatz-Verhältnis: Preis im Verhältnis zum Umsatz.",
            "Price/Sales: Marktkapitalisierung geteilt durch Jahresumsatz."
        )},
        {"Kennzahl": "KBV", "Erklärung": e(
            "Kurs-Buchwert-Verhältnis: Preis im Verhältnis zum Eigenkapital.",
            "Price/Book: Marktkapitalisierung geteilt durch Buchwert des Eigenkapitals."
        )},
        {"Kennzahl": "DivRendite %", "Erklärung": e(
            "Dividende pro Jahr in Prozent des Aktienkurses.",
            "Dividend per Share / Aktienkurs; jährliche Dividendenrendite."
        )},
        {"Kennzahl": "BIP-Wachstum", "Erklärung": e(
            "Wirtschaftswachstum des Landes.",
            "Reales BIP-Wachstum im Jahresvergleich."
        )},
        {"Kennzahl": "Inflation", "Erklärung": e(
            "Teuerungsrate im Land.",
            "Veränderung des Verbraucherpreisindex (CPI) im Jahresvergleich."
        )},
        {"Kennzahl": "Zinsen", "Erklärung": e(
            "Leitzins der Zentralbank.",
            "Offizieller Policy Rate der Notenbank des Landes."
        )},
        {"Kennzahl": "Arbeitslosenquote", "Erklärung": e(
            "Anteil der Arbeitslosen an der Erwerbsbevölkerung.",
            "Saisonbereinigte Arbeitslosenquote in Prozent."
        )},
        {"Kennzahl": "Gewichteter Sharpe", "Erklärung": e(
            "Sharpe Ratio des Gesamtportfolios.",
            "Portfolioweite Sharpe Ratio basierend auf gewichteten Einzelpositionen."
        )},
        {"Kennzahl": "Gewichtete Volatilität", "Erklärung": e(
            "Risiko (Schwankung) des Gesamtportfolios.",
            "Portfoliovolatilität: sqrt(w^T Σ w)."
        )},
    ]

    # Optional: tab-spezifische Ergänzungen
    if tab_type == "aktien":
        return lex
    if tab_type == "laender":
        return [x for x in lex if x["Kennzahl"] in ["BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote"]]
    if tab_type == "portfolio":
        return [x for x in lex if "Gewichtet" in x["Kennzahl"]] + [
            x for x in lex if x["Kennzahl"] in ["1Y %", "Volatilität %", "Sharpe"]
        ]

    return lex

