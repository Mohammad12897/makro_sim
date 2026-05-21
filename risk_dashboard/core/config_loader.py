# risk_dashboard/core/config_loader.py
import yaml
from pathlib import Path

def load_config():
    config_path = Path(__file__).resolve().parents[2] / "risk_dashboard/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
