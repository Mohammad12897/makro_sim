# risk_dashboard/utils/backtest_adapter.py
from typing import Any, Dict
from risk_dashboard.core.macro_pipeline import run_backtest

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
    """
    Adapter, der verschiedene Aufruferformate akzeptiert:
    - positional first arg kann portfolio-dict oder tickers-list sein
    - maps 'prices' -> 'prices_df' falls nötig
    """
    # positional first arg -> possible portfolio
    if args:
        first = args[0]
        tickers = _extract_tickers(first)
        if tickers:
            kwargs.setdefault("tickers", tickers)

    # map 'prices' -> 'prices_df'
    if "prices" in kwargs and "prices_df" not in kwargs:
        kwargs["prices_df"] = kwargs.pop("prices")

    # ensure tickers exist
    if "tickers" not in kwargs or not kwargs["tickers"]:
        raise ValueError("adapter_run_backtest: keine Ticker gefunden")

    return run_backtest(
        kwargs["tickers"],
        kwargs.get("prices_df"),
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
