# risk_dashboard/logging_config.py
import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# --- Safe Formatter / Filter -------------------------------------------------
class SafeFormatter(logging.Formatter):
    """
    Formatter, der fehlende optionale Felder (z. B. run_id) mit Defaultwerten versieht,
    damit logging.format nicht mit ValueError abbricht.
    """
    def format(self, record):
        if not hasattr(record, "run_id"):
            record.run_id = "-"
        # falls weitere optionale Felder benötigt werden, hier ergänzen
        return super().format(record)

class RunIdFilter(logging.Filter):
    def __init__(self, run_id: str = "-"):
        super().__init__()
        self.run_id = run_id
    def filter(self, record):
        if not hasattr(record, "run_id"):
            record.run_id = self.run_id
        return True

# --- BufferHandler (in‑memory log buffer) -----------------------------------
log_buffer: list[str] = []

class BufferHandler(logging.Handler):
    """
    Ein einfacher Handler, der formatierte Log‑Zeilen in einen In‑Memory‑Puffer schreibt.
    Nützlich für UI‑Debug, Tests oder Anzeige im Web‑Frontend.
    """
    def __init__(self, max_entries: int = 200):
        super().__init__()
        self.max_entries = max_entries

    def emit(self, record):
        try:
            msg = self.format(record)
            log_buffer.append(msg)
            # begrenzen: älteste Einträge entfernen
            if len(log_buffer) > self.max_entries:
                del log_buffer[: self.max_entries // 2]
        except Exception:
            # Handler darf niemals Exceptions werfen
            try:
                self.handleError(record)
            except Exception:
                pass

def get_log_buffer() -> list[str]:
    return list(log_buffer)

# --- zentrale Konfiguration --------------------------------------------------
def configure_logging(
    log_level: int = logging.INFO,
    logfile: Optional[str] = None,
    run_id: str = "-",
    enable_buffer: bool = True,
    buffer_level: int = logging.INFO,
):
    """
    Konfiguriert Root‑Logger: StreamHandler + optional RotatingFileHandler + optional BufferHandler.
    Rufe das ganz oben in app.py auf, bevor Module Logs erzeugen.
    """
    fmt_str = "%(asctime)s %(levelname)s [run=%(run_id)s] %(name)s: %(message)s"
    formatter = SafeFormatter(fmt_str)

    root = logging.getLogger()
    # Entferne vorhandene Handler, damit Konfiguration deterministisch ist
    for h in list(root.handlers):
        root.removeHandler(h)

    # Stream handler
    sh = StreamHandler()
    sh.setLevel(log_level)
    sh.setFormatter(formatter)
    sh.addFilter(RunIdFilter(run_id))
    root.addHandler(sh)

    # optional rotating file handler
    if logfile:
        Path(Path(logfile).parent).mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(logfile, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        fh.addFilter(RunIdFilter(run_id))
        root.addHandler(fh)

    # optional buffer handler (in memory)
    if enable_buffer:
        bh = BufferHandler(max_entries=200)
        bh.setLevel(buffer_level)
        bh.setFormatter(formatter)
        bh.addFilter(RunIdFilter(run_id))
        root.addHandler(bh)

    # reduce noisy third-party loggers here if desired
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root.setLevel(log_level)
