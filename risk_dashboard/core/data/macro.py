# core/data/macro.py

def get_country_macro(country: str) -> dict:
    """
    Liefert Makro-Kennzahlen für ein Land.
    Diese Version nutzt statische Beispielwerte.
    Später kannst du echte Datenquellen anbinden (OECD, WorldBank, ECB).
    """

    data = {
        "USA": {
            "BIP-Wachstum": 2.5,
            "Inflation": 3.2,
            "Zinsen": 5.25,
            "Arbeitslosenquote": 3.8,
            "Staatsverschuldung": 120,
            "Währungsstärke": 85,
        },
        "Deutschland": {
            "BIP-Wachstum": 0.6,
            "Inflation": 2.9,
            "Zinsen": 4.50,
            "Arbeitslosenquote": 5.8,
            "Staatsverschuldung": 65,
            "Währungsstärke": 78,
        },
        "Japan": {
            "BIP-Wachstum": 1.2,
            "Inflation": 2.1,
            "Zinsen": 0.10,
            "Arbeitslosenquote": 2.6,
            "Staatsverschuldung": 260,
            "Währungsstärke": 70,
        },
        "UK": {
            "BIP-Wachstum": 1.0,
            "Inflation": 4.0,
            "Zinsen": 5.00,
            "Arbeitslosenquote": 4.2,
            "Staatsverschuldung": 100,
            "Währungsstärke": 80,
        },
        "Frankreich": {
            "BIP-Wachstum": 1.1,
            "Inflation": 3.5,
            "Zinsen": 4.50,
            "Arbeitslosenquote": 7.2,
            "Staatsverschuldung": 112,
            "Währungsstärke": 77,
        },
        "China": {
            "BIP-Wachstum": 4.8,
            "Inflation": 1.2,
            "Zinsen": 3.45,
            "Arbeitslosenquote": 5.0,
            "Staatsverschuldung": 80,
            "Währungsstärke": 65,
        },
        "Indien": {
            "BIP-Wachstum": 6.5,
            "Inflation": 5.4,
            "Zinsen": 6.50,
            "Arbeitslosenquote": 7.8,
            "Staatsverschuldung": 85,
            "Währungsstärke": 60,
        },
    }

    return data.get(country, {
        "BIP-Wachstum": None,
        "Inflation": None,
        "Zinsen": None,
        "Arbeitslosenquote": None,
        "Staatsverschuldung": None,
        "Währungsstärke": None,
    })
