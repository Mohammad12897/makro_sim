# risk_dashboard/core/etf_config.py
import yaml
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path(__file__).parents[1] / "config" / "etf_universe.yaml"

def load_etf_universe(path: Path = CONFIG_PATH) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # Erwartet top-level key 'etf_universe'
    etfs = cfg.get("etf_universe", {})
    # Normalisiere: ensure keys lower/upper or keep as-is
    return etfs

# Beispielnutzung
if __name__ == "__main__":
    etfs = load_etf_universe()
    print(list(etfs.keys()))

# risk_dashboard/core/etf_config.py  (weiter)
from dataclasses import dataclass, field

@dataclass
class ETFMeta:
    name: str
    ticker: str
    asset_class: str
    region: str
    ter_pct: float = field(default=None)
    replication: str = field(default=None)
    isin: str = field(default=None)
    wkn: str = field(default=None)
    distribution: str = field(default=None)
    notes: str = field(default=None)

def build_etf_meta_dict(raw: Dict[str, Dict]) -> Dict[str, ETFMeta]:
    out = {}
    for key, v in raw.items():
        out[key] = ETFMeta(
            name=v.get("name"),
            ticker=v.get("ticker"),
            asset_class=v.get("asset_class"),
            region=v.get("region"),
            ter_pct=v.get("ter_pct"),
            replication=v.get("replication"),
            isin=v.get("isin"),
            wkn=v.get("wkn"),
            distribution=v.get("distribution"),
            notes=v.get("notes"),
        )
    return out
