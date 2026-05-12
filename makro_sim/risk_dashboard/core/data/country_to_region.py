# country_to_region.py
# Erweiterte Zuordnung von Ländern zu Regionen (Groß-/Kleinschreibung wird normalisiert)
country_to_region = {
    # Europa (Auswahl)
    "deutschland": "Europa", "germany": "Europa", "frankreich": "Europa", "france": "Europa",
    "italien": "Europa", "italy": "Europa", "spanien": "Europa", "spain": "Europa",
    "niederlande": "Europa", "netherlands": "Europa", "belgien": "Europa", "belgium": "Europa",
    "schweden": "Europa", "sweden": "Europa", "norwegen": "Europa", "norway": "Europa",
    "dänemark": "Europa", "denmark": "Europa", "uk": "Europa", "united kingdom": "Europa",
    "grossbritannien": "Europa", "britain": "Europa", "österreich": "Europa", "austria": "Europa",
    "schweiz": "Europa", "switzerland": "Europa", "polen": "Europa", "poland": "Europa",
    "portugal": "Europa", "greece": "Europa", "hungary": "Europa", "ungarn": "Europa",

    # Nordamerika / USA
    "usa": "USA", "united states": "USA", "us": "USA", "canada": "Nordamerika", "kanada": "Nordamerika",

    # Asien
    "japan": "Asien", "china": "Asien", "hong kong": "Asien", "south korea": "Asien", "korea": "Asien",
    "singapore": "Asien", "singapur": "Asien", "india": "Asien", "indien": "Asien",

    # Lateinamerika
    "brazil": "Lateinamerika", "brasilien": "Lateinamerika", "mexico": "Lateinamerika", "mexiko": "Lateinamerika",

    # Afrika
    "south africa": "Afrika", "südafrika": "Afrika", "egypt": "Afrika", "nigeria": "Afrika",

    # Ozeanien
    "australia": "Ozeanien", "neuseeland": "Ozeanien", "new zealand": "Ozeanien",

    # Global / Sonstige
    "global": "Global", "welt": "Global", "world": "Global"
}
