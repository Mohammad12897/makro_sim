# core/data/logging.py
import logging

log_buffer = []

class BufferHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_buffer.append(msg)
        # optional: begrenzen
        if len(log_buffer) > 200:
            del log_buffer[:100]

logger = logging.getLogger("risk_dashboard")
logger.setLevel(logging.INFO)

if not logger.handlers:
    bh = BufferHandler()
    bh.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    bh.setFormatter(fmt)
    logger.addHandler(bh)
