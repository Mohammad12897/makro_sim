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

def _call_fn_with_safe_kwargs(fn, *pos_args, **kwargs):
    """
    Wrapper, der kwargs filtert und sicher an fn übergibt.
    Erwartet optional ein kwargs['args'] das eine tuple/list mit positional args enthält.
    """
    # Extrahiere explizit 'args' falls als kw übergeben
    extra_args = ()
    if "args" in kwargs:
        maybe_args = kwargs.pop("args")
        if isinstance(maybe_args, (list, tuple)):
            extra_args = tuple(maybe_args)
        elif maybe_args is None:
            extra_args = ()
        else:
            # falls ein einzelner Wert übergeben wurde, packe ihn in ein tuple
            extra_args = (maybe_args,)

    # Mapping/Filter der erlaubten kwargs wie bisher (deine bestehende Logik)
    call_kwargs = {}
    allowed_keys = getattr(fn, "_allowed_kwargs", None)  # optional
    # Beispiel: mappe nur bestimmte keys; hier deine bestehende Logik verwenden
    for k in ("prices", "weights", "start", "end", "initial_cash", "rebalance", "regimes", "flag_key"):
        if k in kwargs:
            call_kwargs[k] = kwargs[k]

    # Füge pos_args (vom Aufrufer) voran und dann extra_args (aus kwargs['args'])
    final_args = tuple(pos_args) + extra_args

    logger.debug("Mapped call_kwargs keys: %s; remaining ignored kwargs: %s", list(call_kwargs.keys()), [k for k in kwargs.keys() if k not in call_kwargs])
    # Rufe die Funktion mit final_args und call_kwargs auf
    return fn(*final_args, **call_kwargs)

def maybe_run_backtest(run_fn, *args, **kwargs):
    try:
        res = _call_fn_with_safe_kwargs(run_fn, *args, **kwargs)

        ######################################################
        # nach: res = maybe_run_backtest(fn, *args, **kwargs) or {}
        logger.debug("safe_backtest_call: raw envelope returned: %s", repr(res))
        # falls res ein envelope ist, logge auch das result payload
        if isinstance(res, dict) and "result" in res:
            logger.debug("safe_backtest_call: result payload type=%s keys=%s",
                        type(res["result"]), getattr(res["result"], "keys", lambda: None)())
        ######################################################

        # _call_fn_with_safe_kwargs may already return the envelope {"ok":..., "result":...}
        if isinstance(res, dict) and "ok" in res and "result" in res:
            return res
        # otherwise wrap the raw result
        return {"ok": True, "result": res}
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

