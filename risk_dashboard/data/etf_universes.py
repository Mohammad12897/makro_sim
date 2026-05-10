# risk_dashboard/data/etf_universes.py
ETF_UNIVERSES = {
    "ISHARES_CORE_DAX_DE": {
        "name": "iShares Core DAX UCITS ETF (DE)",
        "issuer": "iShares / BlackRock",
        "ticker": "EXS1.DE",        # Beispiel: prÃ¼fe die korrekte Shareclass bei deinem Broker
        "isin": "DE0005933931",
        "wkn": "593393",
        "ter": 0.16,
        "distribution": "Dist",
        "index": "DAX",
        "notes": "Beliebt fÃ¼r SparplÃ¤ne; physische Replikation"
    },
    "AMUNDI_FAZ_100": {
        "name": "Amundi F.A.Z. 100 UCITS ETF",
        "issuer": "Amundi",
        "ticker": "FAZ100.DE",
        "isin": "DE000A2N6A36",
        "ter": 0.15,
        "distribution": "Dist",
        "index": "F.A.Z. 100",
        "notes": "Guter 1â€‘Jahres Performer laut Anbieter"
    },
    "XTRACKERS_DAX": {
        "name": "Xtrackers DAX UCITS ETF",
        "issuer": "Xtrackers / DWS",
        "ticker": "DAXX.DE",
        "isin": "DE000A1E0HR9",
        "ter": None,
        "distribution": "Acc/Dist (je nach Shareclass)",
        "index": "DAX",
        "notes": "Mehrere Shareclasses; prÃ¼fe Acc vs Dist"
    },
    "AMUNDI_DAX50_ESG": {
        "name": "Amundi DAX 50 ESG UCITS ETF",
        "issuer": "Amundi",
        "ticker": "DAX50ESG.DE",
        "isin": "DE000A2N6B44",
        "ter": None,
        "distribution": "Thesaurierend",
        "index": "DAX 50 ESG",
        "notes": "ESGâ€‘angepasste Zusammensetzung"
    }
}

