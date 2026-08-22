# risk_dashboard/utils/backtest_adapter.py
from typing import Any, Dict
from risk_dashboard.core.macro_pipeline import run_backtest
import logging

logger = logging.getLogger(__name__)


def _extract_tickers(arg: Any):
    if isinstance(arg, dict):
        if "tickers" in arg and arg["tickers"]:
            return list(arg["tickers"])
        if "weights" in arg and isinstance(arg["weights"], dict):
            return list(arg["weights"].keys())
    if isinstance(arg, (list, tuple)):
        return list(arg)
    return []

def adapter_run_backtest(*args, **kwargs):
    # 1) extract tickers from first positional arg if present
    if args:
        first = args[0]
        tickers = _extract_tickers(first)  # implementiere passend
        if tickers:
            kwargs.setdefault("tickers", tickers)

    # 2) map 'prices' -> 'prices_df'
    if "prices" in kwargs and "prices_df" not in kwargs:
        kwargs["prices_df"] = kwargs.pop("prices")

    # 3) unify start/end names
    if "start_date" in kwargs and "start" not in kwargs:
        kwargs["start"] = kwargs.pop("start_date")
    if "end_date" in kwargs and "end" not in kwargs:
        kwargs["end"] = kwargs.pop("end_date")

    # 4) map initial_capital -> initial_cash
    if "initial_capital" in kwargs and "initial_cash" not in kwargs:
        kwargs["initial_cash"] = kwargs.pop("initial_capital")

    # 5) map rebalance_freq -> rebalance (optional mapping)
    if "rebalance_freq" in kwargs and "rebalance" not in kwargs:
        freq = kwargs.pop("rebalance_freq")
        if isinstance(freq, str) and freq.upper() == "M":
            kwargs["rebalance"] = "monthly"
        else:
            kwargs["rebalance"] = freq

    if "tickers" not in kwargs or not kwargs["tickers"]:
        raise ValueError("adapter_run_backtest: keine Ticker gefunden")

    result = run_backtest(
        tickers=kwargs.get("tickers"),
        prices_df=kwargs.get("prices_df"),
        start=kwargs.get("start"),
        end=kwargs.get("end"),
        initial_cash=kwargs.get("initial_cash", 10000),
        monthly_dca=kwargs.get("monthly_dca", 0),
        weights=kwargs.get("weights"),
        strategy=kwargs.get("strategy", "equal"),
        momentum_threshold=kwargs.get("momentum_threshold", 0.0),
        vol_target=kwargs.get("vol_target"),
        rebalance=kwargs.get("rebalance", "monthly")
    )

    # ensure dict return
    if isinstance(result, dict):
        return result
    return {"portfolio_value": result, "metrics": {}, "removed_tickers": []}
