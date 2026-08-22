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

def _call_fn_with_safe_kwargs(fn, *args, **kwargs):
    sig = inspect.signature(fn)
    allowed = {
        name for name, param in sig.parameters.items()
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY)
    }
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    removed = [k for k in kwargs.keys() if k not in allowed]
    if removed:
        logger.debug("Removed unexpected kwargs for %s: %s", fn.__name__, removed)
    return fn(*args, **safe_kwargs)

def maybe_run_backtest(run_fn, *args, **kwargs):
    try:
        result = _call_fn_with_safe_kwargs(run_fn, *args, **kwargs)
        return {"ok": True, "result": result}
    except ValueError as e:
        msg = str(e)
        logger.error("maybe_run_backtest: %s", msg)
        return {"ok": False, "error": "no_price_data", "message": msg}
    except TypeError as e:
        logger.exception("maybe_run_backtest TypeError")
        return {"ok": False, "error": "type_error", "message": "Interner Fehler: falsche Parameter an Backtest-Funktion."}
    except Exception:
        logger.exception("maybe_run_backtest: unexpected error")
        return {"ok": False, "error": "internal_error", "message": "Backtest fehlgeschlagen. Details im Log."}
