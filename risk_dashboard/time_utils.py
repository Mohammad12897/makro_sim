# risk_dashboard/time_utils.py
import pandas as pd

def _harmonize_index_tz(df: pd.DataFrame, target_tz="UTC") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    # ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df = df.copy()
            df.index = pd.to_datetime(df.index, errors="coerce")
        except Exception:
            return df
    # if index tz naive and we want tz-aware -> localize
    if df.index.tz is None:
        try:
            df.index = df.index.tz_localize(target_tz)
        except Exception:
            # if localize fails, leave as is
            pass
    else:
        # convert to target tz
        try:
            df.index = df.index.tz_convert(target_tz)
        except Exception:
            pass
    return df

def _make_index_naive(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        try:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        except Exception:
            try:
                df.index = df.index.tz_localize(None)
            except Exception:
                pass
    return df
