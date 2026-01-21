# core/shock_mapping.py

SHOCK_MAP = {
    "Ölpreis +50%": {
        "macro": 0.2,
        "geo": 0.1,
        "energie": 0.8,
        "supply_chain": 0.1
    },
    "Gasembargo": {
        "macro": 0.1,
        "geo": 0.2,
        "energie": 1.0,
        "supply_chain": 0.2,
        "political_security": 0.1
    },
    "Dollar-Schock": {
        "financial": 0.7,
        "currency": 0.5,
        "macro": 0.2
    },
    "USD-Zinsanstieg": {
        "financial": 0.8,
        "currency": 0.4,
        "macro": 0.3
    },
    "SWIFT-Ausschluss": {
        "financial": 0.8,
        "currency": 0.5,
        "geo": 0.3,
        "political_security": 0.2
    },
    "Lieferketten-Blockade": {
        "supply_chain": 1.0,
        "handel": 0.5,
        "macro": 0.2
    },
    "Exportstopp": {
        "handel": 0.8,
        "macro": 0.3,
        "geo": 0.2
    },
    "Technologie-Embargo": {
        "tech": 1.0,
        "geo": 0.3,
        "strategische_autonomie": 0.5
    },
    "Cyberangriff": {
        "tech": 0.8,
        "financial": 0.3,
        "governance": 0.2
    },
    "Geopolitische Spannung": {
        "geo": 1.0,
        "political_security": 0.6,
        "macro": 0.2
    },
    "Bündnisverlust": {
        "political_security": 1.0,
        "geo": 0.8,
        "strategische_autonomie": 0.6
    },
    "Sanktionen": {
        "geo": 0.6,
        "financial": 0.5,
        "handel": 0.4,
        "political_security": 0.3
    }
}


def convert_events_to_shocks(event_list):
    result = {
        "macro": 0,
        "geo": 0,
        "governance": 0,
        "handel": 0,
        "supply_chain": 0,
        "financial": 0,
        "tech": 0,
        "energie": 0,
        "currency": 0,
        "political_security": 0,
        "strategische_autonomie": 0
    }

    for event in event_list:
        name = event["type"]
        intensity = event["intensity"]

        if name not in SHOCK_MAP:
            continue

        for dim, base_value in SHOCK_MAP[name].items():
            result[dim] += base_value * intensity

    # clamp to [0,1]
    for k in result:
        result[k] = min(1.0, result[k])

    return result
