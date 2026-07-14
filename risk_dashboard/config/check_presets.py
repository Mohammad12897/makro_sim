# check_presets.py
import yaml
import sys
from pathlib import Path
import logging
    
logger = logging.getLogger(__name__)

root = Path(".")
u_path = root / "risk_dashboard" / "config" / "etf_universe.yaml"
p_path = root / "risk_dashboard" / "config" / "presets.yaml"

def load_yaml(path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf8")) or {}
    except Exception as e:
        logger.debug(f"Fehler beim Laden {path}: {e}")
        sys.exit(1)

u_raw = load_yaml(u_path)
# Falls die Datei eine Top-Level-Map 'etf_universe' enthält, nutze deren Inhalt
if isinstance(u_raw, dict) and "etf_universe" in u_raw:
    u = u_raw["etf_universe"] or {}
else:
    u = u_raw

p = load_yaml(p_path)

missing = {}
for name, preset in p.get("presets", {}).items():
    for k in preset.get("allowed_keys", []):
        if k not in u:
            missing.setdefault(name, []).append(k)

if missing:
    logger.debug("Fehlende Keys pro Preset:")
    for name, keys in missing.items():
        logger.debug(f"  {name} -> {keys}")
    sys.exit(2)

logger.debug("Validierung OK: alle allowed_keys vorhanden.")
