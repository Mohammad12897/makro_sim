# risk_dashboard/core/safety.py
import re
from pathlib import Path
from typing import Iterable, List, Tuple

DUMP_MARKERS = ["User's Edge browser tabs metadata", "edge_all_open_tabs", "pageTitle"]
EDGE_BLOCK_RE = re.compile(r"(?ms)#\s*User's Edge browser tabs metadata.*$", re.IGNORECASE)
GENERIC_DUMP_RE = re.compile(r"(?ms)edge_all_open_tabs\s*=\s*\[.*?\]\s*", re.IGNORECASE)

def sanitize_text(text: str) -> str:
    if not text:
        return text
    text = EDGE_BLOCK_RE.sub("", text)
    text = GENERIC_DUMP_RE.sub("", text)
    text = re.sub(r"https?://\S+", "<URL_REMOVED>", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL_REMOVED>", text)
    return text

def sanitize_project_pastes(project_root: str, paths: Iterable[str] = None, dry_run: bool = True) -> List[Tuple[str, bool]]:
    root = Path(project_root)
    changed = []
    patterns = ["**/*.py", "**/*.md", "**/*.yml", "**/*.yaml", "**/*.txt"] if paths is None else [str(p) for p in paths]
    files = []
    for p in patterns:
        files.extend(root.glob(p))
    for f in files:
        try:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            if not any(m.lower() in text.lower() for m in DUMP_MARKERS):
                continue
            new = sanitize_text(text)
            if new != text:
                changed.append((str(f), False))
                if not dry_run:
                    backup = f.with_suffix(f.suffix + ".bak")
                    backup.write_text(text, encoding="utf-8")
                    f.write_text(new, encoding="utf-8")
                    changed[-1] = (str(f), True)
        except Exception:
            continue
    return changed

def startup_safety_check(project_root: str, auto_fix: bool = False) -> List[Tuple[str, bool]]:
    return sanitize_project_pastes(project_root, dry_run=not auto_fix)
