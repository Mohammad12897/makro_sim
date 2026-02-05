# core/data/logging.py
import logging

logger = logging.getLogger("risk_dashboard")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)
