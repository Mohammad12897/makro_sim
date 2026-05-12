# risk_dashboard/src/core/glossary.py

GLOSSARY = {
    "Makrovariablen": {
        # Englisch
        "GDP": "Gross Domestic Product – misst den Gesamtwert aller produzierten Güter und Dienstleistungen.",
        "CPIAUCSL": "Consumer Price Index – misst die durchschnittliche Preisveränderung eines Warenkorbs (Inflation).",
        "UNRATE": "Unemployment Rate – Anteil der Arbeitslosen an der Erwerbsbevölkerung.",
        "FEDFUNDS": "Federal Funds Rate – Leitzins der US-Zentralbank.",
        "INDPRO": "Industrial Production Index – misst die Produktionsleistung der Industrie.",
        "M2": "Geldmenge M2 – Bargeld + Einlagen + kurzfristige Geldmarktinstrumente.",

        # Deutsch (Synonyme)
        "BIP": "Bruttoinlandsprodukt – deutsches Synonym für GDP.",
        "Inflation": "Deutscher Begriff für CPI (Consumer Price Index).",
        "Arbeitslosenquote": "Deutscher Begriff für UNRATE.",
        "Leitzins": "Deutscher Begriff für FEDFUNDS.",
        "Industrieproduktion": "Deutscher Begriff für INDPRO.",

        # Allgemein
        "Makrodaten": "Gesamtwirtschaftliche Kennzahlen wie GDP, Inflation, Arbeitslosenquote oder Zinsen.",
        "Makroserien": "Zeitreihen von Makrodaten, z.B. monatliche Inflation oder tägliche Wechselkurse."
    },

    "Modelle": {
        "PCA": "Principal Component Analysis – reduziert mehrere Variablen auf wenige Hauptkomponenten.",
        "Z-Score": "Standardisierte Abweichung vom Mittelwert: (x - μ) / σ.",
        "ARIMA": "Autoregressive Integrated Moving Average – klassisches Zeitreihenmodell für Prognosen.",
        "Prophet": "Forecasting-Modell von Meta – robust gegenüber Ausreißern und saisonalen Mustern.",
        "K-Means": "Clustering-Verfahren zur Erkennung makroökonomischer Regime."
    },

    "Konzepte": {
        "Risk Score": "Aggregierter Risikoindex basierend auf PCA und Makrovariablen.",
        "Regime": "Makroökonomische Zustände wie Expansion, Transition, Rezession.",
        "Scenario Simulation": "Schockanalyse durch Veränderung von Makrovariablen.",
        "Fallback": "Nutzung lokaler Daten, wenn FRED nicht erreichbar ist.",
        "Caching": "Zwischenspeicherung von Daten zur Beschleunigung und Stabilität.",
        "Makro-FX-Zusammenhang": "Makrodaten beeinflussen Wechselkurse: Zinsen ↑ → Währung ↑, Inflation ↑ → Währung ↓.",
        "Makro-Aktien-Zusammenhang": "Makrodaten beeinflussen Aktienmärkte: GDP ↑ → Gewinne ↑ → Aktien ↑.",
        "Investieren": "Investieren basiert auf Makrodaten, Unternehmensdaten und Risikoanalyse.",
        "Warum Makrodaten wichtig sind": "Makrodaten bestimmen Zinsen, Inflation, Wachstum und Risiko – zentrale Treiber aller Finanzmärkte.",

        # Investment-Modul 3.0
        "Risiko-Budget": "Maximales Risiko, das ein Portfolio tragen darf. Steuert den Investitionsgrad.",
        "ETF-Screening": "Systematische Auswahl von ETF-Typen basierend auf Makro-Regimen.",
        "Portfolio-Backtesting": "Simulation einer Strategie auf historischen Daten zur Analyse von Performance und Risiko.",
        "Regime-Backtesting": "Backtest, der historische makroökonomische Regime nutzt, um eine Equity-Kurve zu erzeugen."
    },

    "Strategien": {
        "Regime-basierte Handelsstrategie":
            "Handelsansatz, bei dem die Allokation von Anlageklassen vom makroökonomischen Regime abhängt. "
            "Low Risk → Aktienübergewicht; High Risk → Gold, Anleihen, Defensive.",
        "Makro-Asset-Allocation":
            "Allokation von Kapital basierend auf Makro-Trends, Regimen und Risiko."
    },

    "Investment-Empfehlungen nach Wirtschaftslage": {
        "Wachstum (GDP ↑, UNRATE ↓)":
            "Begünstigt: Aktien allgemein, Tech, Industrie, Konsum, Growth-ETF, Emerging Markets.",
        "Hohe Inflation (CPI ↑)":
            "Begünstigt: Rohstoffe, Energie-ETF, Value-Aktien. Belastet: Tech, Wachstumsaktien.",
        "Steigende Zinsen (FEDFUNDS ↑)":
            "Begünstigt: Banken, Versicherungen, Geldmarkt-ETF. Belastet: Immobilien, Tech, langlaufende Anleihen.",
        "Steigende Arbeitslosigkeit (UNRATE ↑)":
            "Begünstigt: Defensive Sektoren, Minimum-Volatility-ETF, Gold.",
        "Rezession (GDP ↓, INDPRO ↓)":
            "Begünstigt: Staatsanleihen, Gold, defensive Aktien, Low-Volatility-ETF."
    },

    "Datenquellen": {
        "FRED API": "Federal Reserve Economic Data – zentrale Quelle für US-Makrodaten.",
        "BLS": "Bureau of Labor Statistics – Arbeitsmarkt- und Inflationsdaten.",
        "BEA": "Bureau of Economic Analysis – GDP, Einkommen, Konsum."
    }
}


# ---------------------------------------------------------
# OPTIONAL: Alias-System (Deutsch → Englisch)
# ---------------------------------------------------------
ALIASES = {
    "BIP": "GDP",
    "Inflation": "CPIAUCSL",
    "Arbeitslosenquote": "UNRATE",
    "Leitzins": "FEDFUNDS",
    "Industrieproduktion": "INDPRO"
}


def get_definition(term: str):
    """Gibt die Definition eines Begriffs zurück oder None."""
    # Alias auflösen
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
