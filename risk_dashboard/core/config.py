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

def load_etf_universe(path: Optional[Path] = None) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Lädt das ETF-Universe und validiert 'components' Verweise.
    Rückgabe: (universe_dict, validation_warnings)
    """
    p = Path(path) if path else ETF_UNIVERSE_PATH
    if not p.exists():
        return {}, ["etf_universe.yaml nicht gefunden"]
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    universe = data.get("etf_universe", data)
    warnings: List[str] = []

    # Validierung: components referenzieren gültige Keys
    for key, meta in universe.items():
        comps = meta.get("components")
        if comps and isinstance(comps, dict):
            for comp_key in comps.keys():
                if comp_key not in universe:
                    warnings.append(f"'{key}' verweist auf fehlende Komponente '{comp_key}'")

    return universe, warnings

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

