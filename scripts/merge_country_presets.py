#!/usr/bin/env python3
# coding: utf-8
"""
Merge presets/preset_*.json into presets/country_presets.json

- Jede Datei preset_*.json enthält ein Länder-Preset mit Indicator-Snapshot + Metadaten.
- Der Output ist ein Dict: { "BR": {...}, "DE": {...}, ... } in country_presets.json.

Usage:
  python scripts/merge_country_presets.py [--strategy overwrite|skip|rename]
"""

from __future__ import annotations
import json
import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

PRESETS_DIR = Path("presets")
OUT_FILE = PRESETS_DIR / "country_presets.json"


def atomic_write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = NamedTemporaryFile(delete=False, dir=str(path.parent), suffix=".tmp")
    tmp.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    tmp.close()
    Path(tmp.name).replace(path)


def load_json_safe(p: Path):
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to parse {p}: {e}")
        return None


def merge_country_presets(strategy: str = "overwrite") -> dict:
    merged: dict[str, dict] = {}
    files = sorted(PRESETS_DIR.glob("preset_*.json"))

    for p in files:
        data = load_json_safe(p)
        if data is None:
            continue

        # Name ableiten:
        # - Wenn Datei {"BR": {...}} etc. → Key verwenden
        # - Sonst: Dateiname ohne prefix
        if isinstance(data, dict) and len(data) == 1:
            only_key = next(iter(data.keys()))
            only_val = data[only_key]
            if isinstance(only_val, dict) and len(only_key) <= 5 and only_key.isalpha():
                name = only_key
                content = only_val
            else:
                name = p.stem.replace("preset_", "")
                content = data
        else:
            name = p.stem.replace("preset_", "")
            content = data

        # Konflikte behandeln
        if name in merged:
            if strategy == "skip":
                print(f"Skipping duplicate {name} from {p}")
                continue
            if strategy == "rename":
                i = 1
                candidate = f"{name}_{i}"
                while candidate in merged:
                    i += 1
                    candidate = f"{name}_{i}"
                name = candidate

        merged[name] = content

    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        choices=["overwrite", "skip", "rename"],
        default="overwrite",
        help="How to handle duplicate preset names (default: overwrite)",
    )
    args = parser.parse_args()
    merged = merge_country_presets(strategy=args.strategy)
    try:
        atomic_write(OUT_FILE, merged)
        print(f"Wrote {OUT_FILE} with {len(merged)} country presets")
    except Exception as e:
        print("Failed to write country_presets.json:", e)


if __name__ == "__main__":
    main()
