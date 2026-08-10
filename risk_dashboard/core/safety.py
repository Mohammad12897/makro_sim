# scripts/safety.py
from pathlib import Path

def _has_paste_block(text: str) -> bool:
    return "
