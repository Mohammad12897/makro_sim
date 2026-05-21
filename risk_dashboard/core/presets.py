# core/presets.py

import json
import os

def load_presets():
    path = os.path.join("data", "slider_presets.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

