# src/etl/transforms.py
import pandas as pd, numpy as np
from .fetchers import DataAPI
from .persistence import store_indicator
def fetch_reserves(api: DataAPI):
    cb = api.get("central_bank_reserves"); imp = api.get("monthly_imports")
    def normalize(df, value_col):
        if not isinstance(df, pd.DataFrame): df = pd.DataFrame(df)
        if "ts" not in df.columns: df.rename(columns={df.columns[0]:"ts"}, inplace=True)
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=["ts", value_col]).sort_values("ts")
        return df.set_index("ts").resample("ME").last()
    df_res = normalize(cb, "reserves_usd"); df_imp = normalize(imp, "imports_usd")
    df = df_res.join(df_imp, how="inner")
    denom = np.maximum(1.0, df["imports_usd"].values)
    s = pd.Series(df["reserves_usd"].values / denom, index=df.index)
    flag = "ok" if len(s)>0 else "empty"
    path = store_indicator("Reserven_Monate", s, source="CB_API", quality_flag=flag)
    return s, path, flag
