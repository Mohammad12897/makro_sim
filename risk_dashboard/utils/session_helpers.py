# risk_dashboard/utils/session_helpers.py
import inspect
import logging

logger = logging.getLogger(__name__)

try:
    import streamlit as st
except Exception:
    # Minimaler Shim, damit das Modul auch ohne Streamlit importierbar ist (z.B. Tests)
    class _StreamlitShim:
        def __init__(self):
            self._state = {}

        def __getattr__(self, name):
            if name == "session_state":
                return self._state
            # einfache no-op Methoden für write/error etc.
            def _noop(*args, **kwargs): 
                return None
            return _noop

    st = _StreamlitShim()

def maybe_run_backtest(run_fn, *args, **kwargs):
    """
    Versucht run_fn auszuführen, filtert vorher alle kwargs heraus,
    die run_fn nicht in seiner Signatur hat.
    """
    try:
        sig = inspect.signature(run_fn)
        allowed = set(sig.parameters.keys())
        # Entferne 'self' falls Methoden übergeben werden; safe_kwargs enthält nur erlaubte Keys
        safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if len(safe_kwargs) != len(kwargs):
            removed = set(kwargs.keys()) - set(safe_kwargs.keys())
            logger.debug("maybe_run_backtest: entferne unbekannte kwargs %s bevor run_fn aufgerufen wird", removed)
        return run_fn(*args, **safe_kwargs)
    except Exception as exc:
        logger.exception("maybe_run_backtest: run_fn raised an exception")
        raise
