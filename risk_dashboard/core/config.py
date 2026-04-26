from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = CONFIG_DIR / "profiles.yaml"

def load_profiles():
    if not CONFIG_PATH.exists():
        return {"profiles": {}}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"profiles": {}}

def save_profile(key: str, profile: dict):
    data = load_profiles()
    data.setdefault("profiles", {})
    data["profiles"][key] = profile
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)