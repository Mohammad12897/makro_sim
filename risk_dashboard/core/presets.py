# core/presets.py

import json
import os

def load_presets():
    path = os.path.join("data", "slider_presets.json")
    with open(path, "r") as f:
        return json.load(f)
