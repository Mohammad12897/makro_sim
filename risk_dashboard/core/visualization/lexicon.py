#core/visualization/lexicon.py

def _mode_text(mode: str, ein: str, exp: str) -> str:
    return exp if mode == "experte" else ein


LEXIKON = {
    "performance": [