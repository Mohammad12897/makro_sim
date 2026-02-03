#core/visualization/lexicon.py

def _mode_text(mode: str, ein: str, exp: str) -> str:
    return exp if mode == "experte" else ein


LEXIKON = {
    "performance": [
        {
            "Kennzahl": "1Y %",
            "key": "1Y %",
            "einsteiger": "Rendite der letzten 12 Monate. < 0% = negativ, 0–10% = moderat, 10–20% = gut, > 20% = sehr stark.",
            "experte": "Total Return der letzten ca. 252 Handelstage. Annualisierte Rendite > 15% = Outperformance, < 5% = Underperformance."
        },
        {
            "Kennzahl": "5Y %",
            "key": "5Y %",
            "einsteiger": "Rendite der letzten 5 Jahre. Langfristige Entwicklung.",
            "experte": "Annualisierte Rendite über 5 Jahre. > 10% p.a. = stark, < 4% p.a. = schwach."
        },
    ],
    "risiko": [
        {
            "Kennzahl": "Volatilität %",
            "key": "Volatilität %",
            "einsteiger": "Wie stark die Aktie schwankt. < 15% = stabil, 15–25% = normal, > 25% = volatil.",
            "experte": "Standardabweichung der täglichen Renditen. < 12% = Low-Vol, 12–20% = Standard, > 30% = High-Risk."
        },
        {
            "Kennzahl": "Sharpe",
            "key": "Sharpe",
            "einsteiger": "Rendite pro Risikoeinheit. < 0 = schlecht, 0–1 = schwach, 1–2 = gut, > 2 = sehr gut.",
            "experte": "Sharpe = (R_p − R_f) / σ_p. > 1.0 = akzeptabel, > 1.5 = attraktiv, > 2.0 = exzellent."
        },
        {
            "Kennzahl": "Max Drawdown %",
            "key": "Max Drawdown %",
            "einsteiger": "Größter historischer Verlust vom Hoch zum Tief. < -20% = normal, < -40% = hoch, < -60% = extrem.",
            "experte": "Maximaler kumulierter Verlust relativ zum vorherigen Höchststand; Tiefe + Dauer = Krisenresilienz."
        },
        {
            "Kennzahl": "Beta",
            "key": "Beta",
            "einsteiger": "Sensitivität gegenüber dem Markt. Beta = 1: wie der Markt, > 1: risikoreicher, < 1: defensiver.",
            "experte": "Kovarianz(Aktie, Markt) / Varianz(Markt). 0.8–1.2 = marktneutral, > 1.3 = zyklisch, < 0.8 = defensiv."
        },
    ],
    "fundamental": [
        {
            "Kennzahl": "KGV",
            "key": "KGV",
            "einsteiger": "Kurs-Gewinn-Verhältnis. < 10 = günstig, 10–20 = fair, > 20 = teuer.",
            "experte": "Price/Earnings. Tech: 20–40 normal, Value: 8–15 normal, KGV < 5 oft Warnsignal."
        },
        {
            "Kennzahl": "KUV",
            "key": "KUV",
            "einsteiger": "Kurs-Umsatz-Verhältnis. < 2 = günstig, 2–5 = normal, > 5 = teuer.",
            "experte": "Price/Sales. SaaS: 8–15 normal, Industrie: 1–3 normal."
        },
        {
            "Kennzahl": "KBV",
            "key": "KBV",
            "einsteiger": "Kurs-Buchwert-Verhältnis. < 1 = unter Buchwert, 1–3 = normal, > 3 = teuer.",
            "experte": "Price/Book. Banken: KBV < 1 kritisch, Tech: KBV > 5 normal."
        },
        {
            "Kennzahl": "DivRendite %",
            "key": "DivRendite %",
            "einsteiger": "Dividende pro Jahr in % des Kurses. < 2% = niedrig, 2–4% = normal, > 4% = hoch.",
            "experte": "Dividend per Share / Kurs. > 6% oft Dividendenfalle, 3–5% stabil, < 1% Wachstumsaktien."
        },
    ],
    "makro": [
        {
            "Kennzahl": "BIP-Wachstum",
            "key": "BIP-Wachstum",
            "einsteiger": "Wirtschaftswachstum des Landes. < 1% = schwach, 1–3% = normal, > 3% = stark.",
            "experte": "Reales BIP-Wachstum. EM: 4–6% normal, DM: 1.5–2.5% normal."
        },
        {
            "Kennzahl": "Inflation",
            "key": "Inflation",
            "einsteiger": "Teuerungsrate. < 2% = stabil, 2–5% = moderat, > 5% = hoch.",
            "experte": "CPI YoY. > 8% = makroökonomische Stresszone."
        },
        {
            "Kennzahl": "Zinsen",
            "key": "Zinsen",
            "einsteiger": "Leitzins der Zentralbank. < 1% = sehr günstig, 1–3% = normal, > 3% = restriktiv.",
            "experte": "Policy Rate. Realzins = Zins − Inflation; Realzins > 0 = restriktiv, < 0 = expansiv."
        },
        {
            "Kennzahl": "Arbeitslosenquote",
            "key": "Arbeitslosenquote",
            "einsteiger": "Anteil der Arbeitslosen. < 4% = sehr gut, 4–7% = normal, > 7% = schwach.",
            "experte": "Saisonbereinigte Arbeitslosenquote; Vergleich zur NAIRU für Inflationsdruck."
        },
    ],
    "portfolio": [
        {
            "Kennzahl": "Gewichteter Sharpe",
            "key": "Gewichteter Sharpe",
            "einsteiger": "Sharpe Ratio des Gesamtportfolios. > 1 = gut, > 2 = sehr gut.",
            "experte": "Portfolioweite Sharpe Ratio; > 1.5 = effizientes Portfolio."
        },
        {
            "Kennzahl": "Gewichtete Volatilität",
            "key": "Gewichtete Volatilität",
            "einsteiger": "Risiko des Gesamtportfolios. < 10% = defensiv, 10–20% = ausgewogen, > 20% = risikoreich.",
            "experte": "Portfoliovolatilität: sqrt(w^T Σ w)."
        },
    ],
}


META_EINTRAEGE = [
    {
        "Kennzahl": "Radar Aktien",
        "key": "Radar Aktien",
        "einsteiger": "Zeigt Stärken und Schwächen einer Aktie in Performance, Risiko, Bewertung und Makro-Umfeld.",
        "experte": "Visualisiert die Aktie entlang von Performance-, Risiko-, Bewertungs- und Makro-Dimensionen, normiert auf 0–1."
    }
]


def get_lexicon(tab_type: str, mode: str = "einsteiger"):
    if tab_type == "aktien":
        entries = META_EINTRAEGE + \
                  LEXIKON["performance"] + \
                  LEXIKON["risiko"] + \
                  LEXIKON["fundamental"] + \
                  LEXIKON["makro"]
    elif tab_type == "laender":
        entries = LEXIKON["makro"]
    elif tab_type == "portfolio":
        entries = LEXIKON["portfolio"] + LEXIKON["risiko"] + LEXIKON["performance"]
    else:
        entries = []
        for cat in LEXIKON.values():
            entries.extend(cat)

    result = []
    for e in entries:
        result.append({
            "Kennzahl": e["Kennzahl"],
            "Erklärung": _mode_text(mode, e["einsteiger"], e["experte"])
        })
    return result


def get_tooltip_map_for_tab(tab_type: str, mode: str = "einsteiger"):
    lex = get_lexicon(tab_type, mode)
    return {entry["Kennzahl"]: entry["Erklärung"] for entry in lex}
