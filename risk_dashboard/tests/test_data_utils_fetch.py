# tests/test_data_utils_fetch.py
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
import re
import inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import pytest
from unittest.mock import patch
from risk_dashboard.data_utils import fetch_price_history_bulk

def make_df():
    idx = pd.date_range("2020-01-01", periods=3, freq="D")
    return pd.DataFrame({"A": [1,2,3]}, index=idx)

@patch("risk_dashboard.data_utils.safe_fetch")
def test_fetch_price_history_bulk_success(mock_safe_fetch):
    df = make_df()
    mock_safe_fetch.return_value = df
    res = fetch_price_history_bulk(["A"], start="2020-01-01", end="2020-01-03", allow_empty=False)
    assert "A" in res
    assert isinstance(res["A"], pd.Series)
