import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# jetzt funktionieren relative Top-Level-Imports wie `from core.utils import ...`

from risk_dashboard.core.market_engine import to_naive_utc

def test_to_naive_utc_mixed():
    idx_naive = pd.date_range("2020-01-01", periods=3, freq="D")
    s_naive = pd.Series([1,2,3], index=idx_naive)

    idx_aware = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    s_aware = pd.Series([4,5,6], index=idx_aware)

    s_aware_conv = to_naive_utc(s_aware)
    assert getattr(s_aware_conv.index, "tz", None) is None

    df = pd.concat([s_naive.rename("n"), s_aware_conv.rename("a")], axis=1)
    assert "n" in df.columns and "a" in df.columns
    assert not df.empty
