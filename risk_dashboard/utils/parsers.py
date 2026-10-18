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


def safe_head_preview(df, dump_markers=None, max_chars=1000):
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


def parse_quick_add(text: str, default_qty: float = 1.0):
    """
    Parse a quick-add text into a list of (ticker, quantity) tuples.
    Accepted separators between entries: comma, semicolon, newline.
    Accepted ticker/qty separators: colon, equals, whitespace.
    Examples:
      "DAX 2,BTC:3" -> [("DAX", 2.0), ("BTC", 3.0)]
      "NVDA; ETH=0.5\nAAPL" -> [("NVDA", 1.0), ("ETH", 0.5), ("AAPL", 1.0)]
    Returns: List[Tuple[str, float]]
    """
    if not text or not isinstance(text, str):
        return []

    out = []
    # split entries by comma, semicolon or newline
    items = re.split(r'[,\n;]+', text)
    # patterns for ticker+qty and ticker only
    # ticker: letters, numbers, dot, dash; qty: integer or decimal (dot or comma)
    pair_re = re.compile(r'^\s*([A-Za-z0-9\.\-]+)\s*(?:[:=]|\s)\s*([0-9]+(?:[.,][0-9]+)?)\s*$', flags=re.IGNORECASE)
    ticker_only_re = re.compile(r'^\s*([A-Za-z0-9\.\-]+)\s*$', flags=re.IGNORECASE)

    for it in items:
        it = it.strip()
        if not it:
            continue

        # try explicit pair first (supports "BTC:3", "ETH=0.5", "DAX 2")
        m = pair_re.match(it)
        if m:
            ticker = m.group(1).upper()
            qty_raw = m.group(2).replace(',', '.')
            try:
                qty = float(qty_raw)
            except Exception:
                logger.debug("parse_quick_add: invalid quantity '%s' for '%s', using default %s", qty_raw, ticker, default_qty)
                qty = float(default_qty)
            out.append((ticker, qty))
            continue

        # try formats like "DAX2" (ticker immediately followed by digits)
        m2 = re.match(r'^\s*([A-Za-z\.\-]+)([0-9]+(?:[.,][0-9]+)?)\s*$', it)
        if m2:
            ticker = m2.group(1).upper()
            qty_raw = m2.group(2).replace(',', '.')
            try:
                qty = float(qty_raw)
            except Exception:
                qty = float(default_qty)
            out.append((ticker, qty))
            continue

        # ticker only
        t = ticker_only_re.match(it)
        if t:
            ticker = t.group(1).upper()
            out.append((ticker, float(default_qty)))
            continue

        # fallback: try to extract first token as ticker and last token as number
        tokens = re.split(r'\s+', it)
        if tokens:
            first = tokens[0]
            last = tokens[-1]
            # if last token looks like a number, use it as qty
            if re.match(r'^[0-9]+(?:[.,][0-9]+)?$', last):
                try:
                    qty = float(last.replace(',', '.'))
                except Exception:
                    qty = float(default_qty)
                out.append((first.upper(), qty))
                continue
            # otherwise treat whole token as ticker
            out.append((first.upper(), float(default_qty)))
            continue

        logger.debug("parse_quick_add: could not parse '%s'", it)

    return out
