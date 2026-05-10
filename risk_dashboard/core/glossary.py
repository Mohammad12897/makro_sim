# risk_dashboard/src/core/glossary.py

GLOSSARY = {
    "Makrovariablen": {
        # Englisch
        "GDP": "Gross Domestic Product â€“ misst den Gesamtwert aller produzierten GÃ¼ter und Dienstleistungen.",
        "CPIAUCSL": "Consumer Price Index â€“ misst die durchschnittliche PreisverÃ¤nderung eines Warenkorbs (Inflation).",
        "UNRATE": "Unemployment Rate â€“ Anteil der Arbeitslosen an der ErwerbsbevÃ¶lkerung.",
        "FEDFUNDS": "Federal Funds Rate â€“ Leitzins der US-Zentralbank.",
        "INDPRO": "Industrial Production Index â€“ misst die Produktionsleistung der Industrie.",
        "M2": "Geldmenge M2 â€“ Bargeld + Einlagen + kurzfristige Geldmarktinstrumente.",

        # Deutsch (Synonyme)
        "BIP": "Bruttoinlandsprodukt â€“ deutsches Synonym fÃ¼r GDP.",
        "Inflation": "Deutscher Begriff fÃ¼r CPI (Consumer Price Index).",
        "Arbeitslosenquote": "Deutscher Begriff fÃ¼r UNRATE.",
        "Leitzins": "Deutscher Begriff fÃ¼r FEDFUNDS.",
        "Industrieproduktion": "Deutscher Begriff fÃ¼r INDPRO.",

        # Allgemein
        "Makrodaten": "Gesamtwirtschaftliche Kennzahlen wie GDP, Inflation, Arbeitslosenquote oder Zinsen.",
        "Makroserien": "Zeitreihen von Makrodaten, z.B. monatliche Inflation oder tÃ¤gliche Wechselkurse."
    },

    "Modelle": {
        "PCA": "Principal Component Analysis â€“ reduziert mehrere Variablen auf wenige Hauptkomponenten.",
        "Z-Score": "Standardisierte Abweichung vom Mittelwert: (x - Î¼) / Ïƒ.",
        "ARIMA": "Autoregressive Integrated Moving Average â€“ klassisches Zeitreihenmodell fÃ¼r Prognosen.",
        "Prophet": "Forecasting-Modell von Meta â€“ robust gegenÃ¼ber AusreiÃŸern und saisonalen Mustern.",
        "K-Means": "Clustering-Verfahren zur Erkennung makroÃ¶konomischer Regime."
    },

    "Konzepte": {
        "Risk Score": "Aggregierter Risikoindex basierend auf PCA und Makrovariablen.",
        "Regime": "MakroÃ¶konomische ZustÃ¤nde wie Expansion, Transition, Rezession.",
        "Scenario Simulation": "Schockanalyse durch VerÃ¤nderung von Makrovariablen.",
        "Fallback": "Nutzung lokaler Daten, wenn FRED nicht erreichbar ist.",
        "Caching": "Zwischenspeicherung von Daten zur Beschleunigung und StabilitÃ¤t.",
        "Makro-FX-Zusammenhang": "Makrodaten beeinflussen Wechselkurse: Zinsen â†‘ â†’ WÃ¤hrung â†‘, Inflation â†‘ â†’ WÃ¤hrung â†“.",
        "Makro-Aktien-Zusammenhang": "Makrodaten beeinflussen AktienmÃ¤rkte: GDP â†‘ â†’ Gewinne â†‘ â†’ Aktien â†‘.",
        "Investieren": "Investieren basiert auf Makrodaten, Unternehmensdaten und Risikoanalyse.",
        "Warum Makrodaten wichtig sind": "Makrodaten bestimmen Zinsen, Inflation, Wachstum und Risiko â€“ zentrale Treiber aller FinanzmÃ¤rkte.",

        # Investment-Modul 3.0
        "Risiko-Budget": "Maximales Risiko, das ein Portfolio tragen darf. Steuert den Investitionsgrad.",
        "ETF-Screening": "Systematische Auswahl von ETF-Typen basierend auf Makro-Regimen.",
        "Portfolio-Backtesting": "Simulation einer Strategie auf historischen Daten zur Analyse von Performance und Risiko.",
        "Regime-Backtesting": "Backtest, der historische makroÃ¶konomische Regime nutzt, um eine Equity-Kurve zu erzeugen."
    },

    "Strategien": {
        "Regime-basierte Handelsstrategie":
            "Handelsansatz, bei dem die Allokation von Anlageklassen vom makroÃ¶konomischen Regime abhÃ¤ngt. "
            "Low Risk â†’ AktienÃ¼bergewicht; High Risk â†’ Gold, Anleihen, Defensive.",
        "Makro-Asset-Allocation":
            "Allokation von Kapital basierend auf Makro-Trends, Regimen und Risiko."
    },

    "Investment-Empfehlungen nach Wirtschaftslage": {
        "Wachstum (GDP â†‘, UNRATE â†“)":
            "BegÃ¼nstigt: Aktien allgemein, Tech, Industrie, Konsum, Growth-ETF, Emerging Markets.",
        "Hohe Inflation (CPI â†‘)":
            "BegÃ¼nstigt: Rohstoffe, Energie-ETF, Value-Aktien. Belastet: Tech, Wachstumsaktien.",
        "Steigende Zinsen (FEDFUNDS â†‘)":
            "BegÃ¼nstigt: Banken, Versicherungen, Geldmarkt-ETF. Belastet: Immobilien, Tech, langlaufende Anleihen.",
        "Steigende Arbeitslosigkeit (UNRATE â†‘)":
            "BegÃ¼nstigt: Defensive Sektoren, Minimum-Volatility-ETF, Gold.",
        "Rezession (GDP â†“, INDPRO â†“)":
            "BegÃ¼nstigt: Staatsanleihen, Gold, defensive Aktien, Low-Volatility-ETF."
    },

    "Datenquellen": {
        "FRED API": "Federal Reserve Economic Data â€“ zentrale Quelle fÃ¼r US-Makrodaten.",
        "BLS": "Bureau of Labor Statistics â€“ Arbeitsmarkt- und Inflationsdaten.",
        "BEA": "Bureau of Economic Analysis â€“ GDP, Einkommen, Konsum."
    }
}


# ---------------------------------------------------------
# OPTIONAL: Alias-System (Deutsch â†’ Englisch)
# ---------------------------------------------------------
ALIASES = {
    "BIP": "GDP",
    "Inflation": "CPIAUCSL",
    "Arbeitslosenquote": "UNRATE",
    "Leitzins": "FEDFUNDS",
    "Industrieproduktion": "INDPRO"
}


def get_definition(term: str):
    """Gibt die Definition eines Begriffs zurÃ¼ck oder None."""
    # Alias auflÃ¶sen
    if term in ALIASES:
        term = ALIASES[term]

    for category, items in GLOSSARY.items():
        if term in items:
            return items[term]
    return None


def search_glossary(query: str):
    """Durchsucht das gesamte Glossar nach Begriffen oder Textstellen."""
    if not query:
        return []

    query = query.lower()
    results = []

    # Alias-Suche
    if query in ALIASES:
        query = ALIASES[query].lower()

    for category, items in GLOSSARY.items():
        for term, definition in items.items():
            if query in term.lower() or query in definition.lower():
                results.append((category, term, definition))

    return results

