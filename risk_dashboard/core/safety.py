# risk_dashboard/core/safety.py
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Wenn keine Marker in der docs-Datei gefunden werden, liefern wir eine leere Liste zurück.
# Aufrufer müssen prüfen: if not DUMP_MARKERS: -> Fallback verwenden.
DEFAULT_DUMP_MARKERS: List[str] = []

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
                candidates.append(ln_clean)
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

DOC_EXAMPLE = Path(__file__).resolve().parents[1] / "docs" / "edge_tabs_example.txt"
DUMP_MARKERS = _load_markers_from_docs(DOC_EXAMPLE)
