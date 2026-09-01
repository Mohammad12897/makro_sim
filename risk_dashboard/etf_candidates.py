# risk_dashboard/etf_candidates.py
import os
import yaml
from tempfile import NamedTemporaryFile
import shutil

CANDIDATES_FILE = os.path.join(os.path.dirname(__file__), "data", "etf_candidates.yml")

def _ensure_data_dir():
    d = os.path.dirname(CANDIDATES_FILE)
    os.makedirs(d, exist_ok=True)

def load_etf_candidates():
    _ensure_data_dir()
    if not os.path.exists(CANDIDATES_FILE):
        return {}
    with open(CANDIDATES_FILE, "r", encoding="utf8") as f:
        return yaml.safe_load(f) or {}

def add_etf_candidates(index_name: str, tickers: list[str]):
    _ensure_data_dir()
    data = load_etf_candidates()
    data.setdefault(index_name, [])
    for t in tickers:
        if t not in data[index_name]:
            data[index_name].append(t)
    # atomar schreiben
    with NamedTemporaryFile("w", delete=False, dir=os.path.dirname(CANDIDATES_FILE), encoding="utf8") as tf:
        yaml.safe_dump(data, tf, sort_keys=False, allow_unicode=True)
        tmpname = tf.name
    shutil.move(tmpname, CANDIDATES_FILE)
