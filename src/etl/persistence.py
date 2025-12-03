import pandas as pd
from ..config import DATA_DIR
def _write_parquet(df, name):
    path = DATA_DIR / f"{name}.parquet"
    try: df.to_parquet(path, index=False)
    except Exception: df.to_csv(path.with_suffix(".csv"), index=False)
    return path
def store_indicator(name, series, source, quality_flag="ok"):
    df = pd.DataFrame({"indicator_name": name, "value": series.values, "ts": series.index.astype("datetime64[ns]"), "source": source, "quality_flag": quality_flag})
    path = DATA_DIR / f"{name}.parquet"
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df]).drop_duplicates(subset=["ts"]).sort_values("ts")
        except Exception:
            pass
    _write_parquet(df, name)
    return path
