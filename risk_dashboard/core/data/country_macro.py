#core/analysis/data/country_macro.py

# core/data/country_macro.py

COUNTRY_MACRO = {
    "USA": {
        "BIP-Wachstum": 2.5,
        "Inflation": 3.2,
        "Zinsen": 5.25,
        "Arbeitslosenquote": 3.8,
    },
    "Deutschland": {
        "BIP-Wachstum": 0.1,
        "Inflation": 2.8,
        "Zinsen": 4.5,
        "Arbeitslosenquote": 5.6,
    },
    "Japan": {
        "BIP-Wachstum": 1.3,
        "Inflation": 2.1,
        "Zinsen": 0.1,
        "Arbeitslosenquote": 2.5,
    },
    "UK": {
        "BIP-Wachstum": 0.4,
        "Inflation": 3.9,
        "Zinsen": 5.0,
        "Arbeitslosenquote": 4.2,
    },
    "Frankreich": {
        "BIP-Wachstum": 1.0,
        "Inflation": 3.5,
        "Zinsen": 4.5,
        "Arbeitslosenquote": 7.2,
    },
}

def get_country_macro(country: str) -> dict:
    return COUNTRY_MACRO.get(country, {
        "BIP-Wachstum": 0,
        "Inflation": 0,
        "Zinsen": 0,
        "Arbeitslosenquote": 0,
    })
