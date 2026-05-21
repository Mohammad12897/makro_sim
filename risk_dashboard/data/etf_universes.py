# risk_dashboard/data/etf_universes.py
ETF_UNIVERSES = {
    "ISHARES_CORE_DAX_DE": {
        "name": "iShares Core DAX UCITS ETF (DE)",
        "issuer": "iShares / BlackRock",
        "ticker": "EXS1.DE",
        "isin": "DE0005933931",
        "wkn": "593393",
        "ter": 0.16,
        "distribution": "Dist",
        "index": "DAX",
        "notes": "Beliebt für Sparpläne; physische Replikation"
    },

    "AMUNDI_FAZ_100": {
        "name": "iShares MDAX UCITS ETF",
        "issuer": "iShares / BlackRock",
        "ticker": "EXS2.DE",
        "isin": "DE0005933923",
        "ter": 0.51,
        "distribution": "Dist",
        "index": "MDAX",
        "notes": "Ersatz für FAZ‑100; funktionaler DE‑ETF"
    },

    "XTRACKERS_DAX": {
        "name": "Xtrackers DAX UCITS ETF",
        "issuer": "Xtrackers / DWS",
        "ticker": "XDAX.DE",
        "isin": "DE000A1E0HR9",
        "ter": None,
        "distribution": "Acc/Dist (je nach Shareclass)",
        "index": "DAX",
        "notes": "Mehrere Shareclasses; prüfe Acc vs Dist"
    },

    "AMUNDI_DAX50_ESG": {
        "name": "Xtrackers ESG Germany UCITS ETF",
        "issuer": "Xtrackers / DWS",
        "ticker": "XUDE.DE",
        "isin": "DE000A2QM6B1",
        "ter": 0.20,
        "distribution": "Thesaurierend",
        "index": "ESG Germany",
        "notes": "Ersatz für Amundi DAX50 ESG; bei Yahoo verfügbar"
    }
}