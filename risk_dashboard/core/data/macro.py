# core/data/macro.py

def get_country_macro(country: str) -> dict:
    """
    Liefert Makro-Kennzahlen fÃ¼r ein Land.
    Diese Version nutzt statische Beispielwerte.
    SpÃ¤ter kannst du echte Datenquellen anbinden (OECD, WorldBank, ECB).
    """

    data = {
        "USA": {
            "BIP-Wachstum": 2.5,
            "Inflation": 3.2,
            "Zinsen": 5.25,
            "Arbeitslosenquote": 3.8,
            "Staatsverschuldung": 120,
            "WÃ¤hrungsstÃ¤rke": 85,
        },
        "Deutschland": {
            "BIP-Wachstum": 0.6,
            "Inflation": 2.9,
            "Zinsen": 4.50,
            "Arbeitslosenquote": 5.8,
            "Staatsverschuldung": 65,
            "WÃ¤hrungsstÃ¤rke": 78,
        },
        "Japan": {
            "BIP-Wachstum": 1.2,
            "Inflation": 2.1,
            "Zinsen": 0.10,
            "Arbeitslosenquote": 2.6,
            "Staatsverschuldung": 260,
            "WÃ¤hrungsstÃ¤rke": 70,
        },
        "UK": {
            "BIP-Wachstum": 1.0,
            "Inflation": 4.0,
            "Zinsen": 5.00,
            "Arbeitslosenquote": 4.2,
            "Staatsverschuldung": 100,
            "WÃ¤hrungsstÃ¤rke": 80,
        },
        "Frankreich": {
            "BIP-Wachstum": 1.1,
            "Inflation": 3.5,
            "Zinsen": 4.50,
            "Arbeitslosenquote": 7.2,
            "Staatsverschuldung": 112,
            "WÃ¤hrungsstÃ¤rke": 77,
        },
        "China": {
            "BIP-Wachstum": 4.8,
            "Inflation": 1.2,
            "Zinsen": 3.45,
            "Arbeitslosenquote": 5.0,
            "Staatsverschuldung": 80,
            "WÃ¤hrungsstÃ¤rke": 65,
        },
        "Indien": {
            "BIP-Wachstum": 6.5,
            "Inflation": 5.4,
            "Zinsen": 6.50,
            "Arbeitslosenquote": 7.8,
            "Staatsverschuldung": 85,
            "WÃ¤hrungsstÃ¤rke": 60,
        },
    }

    return data.get(country, {
        "BIP-Wachstum": None,
        "Inflation": None,
        "Zinsen": None,
        "Arbeitslosenquote": None,
        "Staatsverschuldung": None,
        "WÃ¤hrungsstÃ¤rke": None,
    })

