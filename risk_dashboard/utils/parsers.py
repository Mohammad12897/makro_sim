# risk_dashboard/core/parsers.py
import re
import tempfile
import streamlit as st
from typing import List, Dict, Tuple
from io import StringIO
import pandas as pd
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

# --- Marker loader (liest kurze tokens aus docs, keine langen Dumps) ---
DEFAULT_DUMP_MARKERS: List[str] = []
DEFAULT_MARKERS_FILE = Path(__file__).parents[1] / "docs" / "default_edge_markers.txt"
DOC_EXAMPLE = Path(__file__).parents[1] / "docs" / "edge_tabs_example.txt"


_QUICK_ADD_PATTERN = re.compile(
    r"""
    (?P<ticker>[A-Za-z0-9\.\-_]+)
    (?:\s*[:\s]\s*
    (?P<qty>-?\d+(\.\d+)?))?
    """,
    re.VERBOSE,
)

def _load_markers_from_docs(doc_path: Path, max_markers: int = 3) -> List[str]:
    try:
        if not doc_path.exists():
            logger.warning("edge tabs example not found: %s", doc_path)
            return []
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        lines = [ln.strip() for ln in text.splitlines()]
        candidates = []
        for ln in lines:
            if not ln:
                continue
            if ln.lstrip().startswith("#"):
                continue
            ln_clean = ln.strip().strip('",').strip("'")
            if ln_clean:
                # keep only short alphanumeric tokens to avoid committing long dumps
                token = re.sub(r'[^A-Za-z0-9_ ]', '', ln_clean).strip()
                if token:
                    candidates.append(token)
            if len(candidates) >= max_markers:
                break
        if not candidates:
            logger.warning("No usable markers found in %s; returning empty marker list.", doc_path)
            return []
        # dedupe while preserving order
        seen = set()
        result = []
        for r in candidates:
            if r not in seen:
                seen.add(r)
                result.append(r)
        return result
    except Exception:
        logger.exception("Failed to load markers from docs")
        return []

DUMP_MARKERS = _load_markers_from_docs(DOC_EXAMPLE) or DEFAULT_DUMP_MARKERS

# --- safe helpers ---
def safe_read_csv(uploaded_file, dump_markers: List[str] | None = None, encoding: str = "utf-8") -> pd.DataFrame:
    """
    Robust CSV reader: entfernt Zeilen, die Dump‑Marker enthalten oder mit '#' beginnen.
    uploaded_file: Streamlit UploadedFile or file-like object
    """
    if dump_markers is None:
        dump_markers = []
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        text = raw.decode(encoding, errors="ignore")
    else:
        text = str(raw)
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        low = s.lower()
        if any(marker.lower() in low for marker in dump_markers):
            # skip suspicious lines that contain any marker token
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    return pd.read_csv(StringIO(cleaned))

def safe_head_preview(df: pd.DataFrame, dump_markers: List[str] | None = None, max_chars: int = 1000) -> str:
    """
    Safe preview for logging/UI: returns a string or a placeholder if suspicious markers found.
    """
    if dump_markers is None:
        dump_markers = []
    try:
        s = df.head().to_string()
    except Exception:
        s = str(df)[:max_chars]
    low = s.lower()
    if any(marker.lower() in low for marker in dump_markers):
        return "<skipped suspicious dump>"
    return s

def parse_quick_add(text: str, default_qty: int = 1) -> List[Dict]:
    if not text:
        return []

    normalized = re.sub(r'[\r\n;]+', ',', text.strip())
    parts = [p.strip() for p in normalized.split(',') if p.strip()]

    results = []
    for part in parts:
        m = _QUICK_ADD_PATTERN.match(part)
        if not m:
            tokens = part.split()
            if len(tokens) == 1:
                ticker = tokens[0].upper()
                qty = default_qty
            elif len(tokens) >= 2:
                ticker = tokens[0].upper()
                try:
                    qty = int(float(tokens[1]))
                except Exception:
                    qty = default_qty
            else:
                continue
        else:
            ticker = m.group("ticker").upper()
            qty_raw = m.group("qty")
            if qty_raw is None:
                qty = default_qty
            else:
                try:
                    qty = int(float(qty_raw))
                except Exception:
                    qty = default_qty

        if qty < 0:
            qty = default_qty
        results.append({"ticker": ticker, "quantity": qty})

    return results
