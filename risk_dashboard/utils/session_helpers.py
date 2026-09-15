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
    """
    Map common kwarg variants to canonical names expected by the adapter/backtest,
    call the target function and normalize the return envelope.
    """
    logger.debug("Entering _call_fn_with_safe_kwargs: fn=%s args=%s kwargs_keys=%s",
                 getattr(fn, "__name__", str(fn)), args, list(kwargs.keys()))

    # Build call_kwargs by mapping known variants to canonical names
    call_kwargs = {}

    # prices mapping (UI may pass 'prices' or 'prices_df')
    if "prices" in kwargs:
        call_kwargs["prices"] = kwargs.pop("prices")
    elif "prices_df" in kwargs:
        call_kwargs["prices"] = kwargs.pop("prices_df")

    # weights mapping (weights or user_weights)
    if "weights" in kwargs:
        call_kwargs["weights"] = kwargs.pop("weights")
    elif "user_weights" in kwargs:
        call_kwargs["weights"] = kwargs.pop("user_weights")

    # start / end
    if "start" in kwargs:
        call_kwargs["start"] = kwargs.pop("start")
    elif "start_date" in kwargs:
        call_kwargs["start"] = kwargs.pop("start_date")

    if "end" in kwargs:
        call_kwargs["end"] = kwargs.pop("end")
    elif "end_date" in kwargs:
        call_kwargs["end"] = kwargs.pop("end_date")

    # initial capital -> initial_cash
    if "initial_capital" in kwargs:
        call_kwargs["initial_cash"] = kwargs.pop("initial_capital")
    elif "initial_cash" in kwargs:
        call_kwargs["initial_cash"] = kwargs.pop("initial_cash")

    # rebalance variants
    if "rebalance" in kwargs:
        call_kwargs["rebalance"] = kwargs.pop("rebalance")
    elif "rebalance_freq" in kwargs:
        freq = kwargs.pop("rebalance_freq")
        call_kwargs["rebalance"] = "monthly" if (isinstance(freq, str) and freq.upper() == "M") else freq

    # optional pass-through keys
    for k in ("regimes", "strategy", "flag_key", "monthly_dca"):
        if k in kwargs:
            call_kwargs[k] = kwargs.pop(k)

    logger.debug("Mapped call_kwargs keys: %s; remaining ignored kwargs: %s",
                 list(call_kwargs.keys()), list(kwargs.keys()))

    # Call the target function
    try:
        result = fn(*args, **call_kwargs)
    except Exception:
        logger.exception("Error calling %s", getattr(fn, "__name__", str(fn)))
        raise

    # Normalize return envelope expected by callers
    if isinstance(result, dict) and "ok" in result and "result" in result:
        return result
    if isinstance(result, dict):
        return {"ok": True, "message": "ok", "result": result}
    return {"ok": True, "message": "ok", "result": result}

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

