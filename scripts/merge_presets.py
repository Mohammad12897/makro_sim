#!/usr/bin/env python3
# coding: utf-8
"""
Merge presets/preset_*.json into presets/presets.json
Each entry in presets.json will contain the full JSON content of the source file.
Usage:
  python scripts/merge_presets_full.py [--strategy overwrite|skip|rename]
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

PRESETS_DIR = Path("presets")
OUT_FILE = PRESETS_DIR / "presets.json"

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

def merge_presets(strategy: str = "overwrite") -> dict:
    merged = {}
    files = sorted(PRESETS_DIR.glob("preset_*.json"))
    for p in files:
        data = load_json_safe(p)
        if data is None:
            continue
        # key name: prefer explicit top-level name if file contains single named preset,
        # otherwise use filename stem without prefix
        # If file is {"DE": {...}} or {"preset_DE": {...}} -> unwrap
        if isinstance(data, dict) and len(data) == 1:
            only_key = next(iter(data.keys()))
            only_val = data[only_key]
            # Heuristics: if only_key looks like a preset name, use it
            if isinstance(only_val, dict) and (only_key.startswith("preset_") or len(only_key) <= 5 or only_key.isalpha()):
                name = only_key.replace("preset_", "")
                content = only_val
            else:
                # treat whole file as content for filename key
                name = p.stem.replace("preset_", "")
                content = data
        else:
            # file contains many keys or arbitrary structure -> use filename key and full content
            name = p.stem.replace("preset_", "")
            content = data

        # handle conflicts
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
    parser.add_argument("--strategy", choices=["overwrite","skip","rename"], default="overwrite",
                        help="How to handle duplicate preset names (default: overwrite)")
    args = parser.parse_args()
    merged = merge_presets(strategy=args.strategy)
    try:
        atomic_write(OUT_FILE, merged)
        print(f"Wrote {OUT_FILE} with {len(merged)} presets")
    except Exception as e:
        print("Failed to write Presets.json:", e)

if __name__ == "__main__":
    main()
