# risk_dashboard/core/config.py
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import yaml
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
ETF_UNIVERSE_PATH = BASE_DIR / "config" / "etf_universe.yaml"
PROFILES_PATH = BASE_DIR / "config" / "profiles.yaml"
AUDIT_LOG_PATH = BASE_DIR / "logs" / "audit_log.jsonl"

def _append_audit(entry: Dict[str, Any]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def load_etf_universe(path="risk_dashboard/config/etf_universe.yaml"):

    warnings = []

    try:
        raw = yaml.safe_load(open(path, "r", encoding="utf8"))
    except Exception as e:
        return {}, [f"YAML-Fehler in {path}: {e}"]

    if raw is None:
        return {}, ["etf_universe.yaml ist leer"]

    # Falls Datei Top-Level-Key 'etf_universe' hat → extrahieren
    if isinstance(raw, dict) and "etf_universe" in raw:
        universe = raw["etf_universe"]
    else:
        universe = raw

    cleaned = {}

    for key, meta in universe.items():

        # ❗ Fehler 1: meta ist kein Dict → Warnung statt Absturz
        if not isinstance(meta, dict):
            warnings.append(
                f"Eintrag '{key}' ist kein Dictionary (Typ: {type(meta).__name__}). "
                f"Vermutlich Einrückungsfehler oder kaputte YAML-Struktur."
            )
            continue

        # ❗ Fehler 2: Komponenten müssen Dict sein
        comps = meta.get("components")
        if comps is not None and not isinstance(comps, dict):
            warnings.append(
                f"ETF '{key}' hat ungültige 'components' (Typ: {type(comps).__name__}). "
                f"Erwartet wird ein Dictionary."
            )
            meta["components"] = None

        # ❗ Fehler 3: Leere Strings oder kaputte Werte entfernen
        for f, v in list(meta.items()):
            if isinstance(v, str) and v.strip() == "":
                warnings.append(f"ETF '{key}' enthält leeren Wert für '{f}' – entfernt.")
                meta.pop(f)

        cleaned[key] = meta

    return cleaned, warnings

def load_profiles(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else PROFILES_PATH
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_profile(key: str, profile_obj: Dict[str, Any], path: Optional[Path] = None) -> None:
    p = Path(path) if path else PROFILES_PATH
    cfg = load_profiles(p)
    profiles = cfg.get("profiles", {}) if isinstance(cfg, dict) else {}
    profiles[key] = profile_obj
    cfg_out = {"profiles": profiles}
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg_out, f, sort_keys=False, allow_unicode=True)
    # Audit
    _append_audit({"action": "save_profile", "key": key, "profile": profile_obj})

