# risk_dashboard/core/safety.py
import re
from pathlib import Path
from typing import Iterable, List, Tuple

DUMP_MARKERS = [
    "User's Edge browser tabs metadata",
    "edge_all_open_tabs",
    "pageTitle"
]

EDGE_BLOCK_RE = re.compile(r"(?ms)