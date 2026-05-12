#core/lexicon.py
import json
import os

LEXICON_PATH = os.path.join("data", "lexicon.json")

def load_lexicon():
    with open(LEXICON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
