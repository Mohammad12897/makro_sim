#!/usr/bin/env python3
# scripts/generate_presets.py
# Erzeugt Preset-JSONs für Länder basierend auf src.etl.DataAPI und src.etl.transforms
# Robust: timezone-aware timestamps, Backup, Debug-Logging, optional test_overrides

import sys
from pathlib import Path
from datetime import datetime, timezone
import json

# Sicherstellen, dass Projekt-Root im sys.path ist (macht das Script portabel)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.fetchers import DataAPI
from src.etl.transforms import map_indicators_to_preset

# Ausgabe-Pfade
OUT = Path("data/presets.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = OUT.parent / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Länderliste: ISO2 -> Reporter (optional)
COUNTRIES = {
    "DE": {"iso": "DE", "reporter": "276"},
    "CN": {"iso": "CN", "reporter": "156"},
    "US": {"iso": "US", "reporter": "840"},
    "IR": {"iso": "IR", "reporter": "364"},
    "BR": {"iso": "BR", "reporter": "076"},
    "IN": {"iso": "IN", "reporter": "356"},
}

def load_existing():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding="utf-8"))
        except Exception as e:
            print("[load_existing] failed to read existing presets:", e)
            return {}
    return {}

def backup_existing():
    if OUT.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        b = BACKUP_DIR / f"presets_{ts}.json"
        try:
            b.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
            print("Backup written:", b)
        except Exception as e:
            print("[backup_existing] failed to write backup:", e)

def build_for_country(code, meta):
    print("Processing", code)
    api = DataAPI(country_iso=meta["iso"], reporter_code=meta.get("reporter", ""))
    # --- Optional: temporäre Test-Overrides für Debug (auskommentieren im Produktivbetrieb) ---
    # if code == "DE":
    #     api.test_overrides = {"reserves_usd": 250e9, "monthly_imports_usd": 147e9, "cofer_usd_share": 0.55}
    # elif code == "CN":
    #     api.test_overrides = {"reserves_usd": 3200e9, "monthly_imports_usd": 268e9, "cofer_usd_share": 0.50}
    # ------------------------------------------------------------------------------

    inds = api.build_indicators_snapshot()
    # Debug: zeige verwendete Indikatoren
    try:
        print(f"{code} indicators:", json.dumps(inds, indent=2, ensure_ascii=False))
    except Exception:
        print(f"{code} indicators: (could not pretty-print)")

    # Markiere, ob lokale COFER/Reserves-Dateien vorhanden sind
    inds["cofer_present"] = bool(api.cache_dir.joinpath(f"cofer_{code}.json").exists() or api.cache_dir.joinpath(f"cofer_{code}.csv").exists())
    inds["reserves_local_present"] = bool(api.cache_dir.joinpath(f"reserves_{code}.csv").exists() or api.cache_dir.joinpath(f"reserves_{code}.json").exists())

    preset_params, meta_info = map_indicators_to_preset(inds, country_iso=code)

    # Ergänze/vereinheitliche Metadaten
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "country": code,
        "sources": meta_info.get("source_map", {}),
        "confidence": meta_info.get("confidence", inds.get("confidence", "low")),
        "notes": meta_info.get("notes", "")
    }

    preset_obj = {
        "params": preset_params,
        "metadata": metadata
    }
    return f"preset_{code}", preset_obj

def main():
    existing = load_existing()
    new_presets = {}

    for code, meta in COUNTRIES.items():
        key, preset_obj = build_for_country(code, meta)
        new_presets[key] = preset_obj

    # Backup vorheriger Datei
    backup_existing()

    # Merge (überschreibt gleiche Keys)
    merged = existing.copy()
    merged.update(new_presets)

    try:
        OUT.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Wrote presets:", list(new_presets.keys()))
    except Exception as e:
        print("[main] failed to write presets.json:", e)

if __name__ == "__main__":
    main()
