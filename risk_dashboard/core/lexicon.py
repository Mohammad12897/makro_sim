#core/lexicon.py
import json
import os

LEXICON_PATH_JS = os.path.join("data", "lexicon.json")
LEXICON_PATH_MD = os.path.join("data", "lexicon.md")

def load_lexicon_js():
    with open(LEXICON_PATH_JS, "r", encoding="utf-8") as f:
        return json.load(f)

def load_lexicon():
    with open(LEXICON_PATH_MD, "r", encoding="utf-8") as f:
        return f.read()