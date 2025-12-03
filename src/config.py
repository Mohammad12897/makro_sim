from pathlib import Path
DATA_DIR = Path("/content/drive/MyDrive/makro_sim/data/indicators")
DATA_DIR.mkdir(parents=True, exist_ok=True)
default_params = {
    "USD_Dominanz": 0.7, "RMB_Akzeptanz": 0.2, "Zugangsresilienz": 0.8,
    "Reserven_Monate": 6, "FX_Schockempfindlichkeit": 0.8, "Sanktions_Exposure": 0.05,
    "Alternativnetz_Abdeckung": 0.5, "Liquiditaetsaufschlag": 0.03, "CBDC_Nutzung": 0.5,
    "Golddeckung": 0.4, "innovation": 0.6, "fachkraefte": 0.7, "energie": 0.5,
    "stabilitaet": 0.9, "verschuldung": 0.8, "demokratie": 0.8,
    "country_iso": "DE", "reporter_code": "276"
}
