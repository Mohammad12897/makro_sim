# risk_dashboard/__init__.py
import os
import logging

# logs-Ordner relativ zum Paket
log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
log_dir = os.path.abspath(log_dir)
os.makedirs(log_dir, exist_ok=True)

log_path = os.path.join(log_dir, "risk_dashboard.log")

root_logger = logging.getLogger("risk_dashboard")
if not root_logger.handlers:
    try:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        fh.setFormatter(fmt)
        root_logger.addHandler(fh)
        root_logger.setLevel(logging.DEBUG)
    except Exception as e:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        root_logger.warning("Could not create file logger (%s). Falling back to console logging.", e)
# ---------------------------------------------------------------------