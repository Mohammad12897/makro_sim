# tests/test_duplicates.py
import pandas as pd
from risk_dashboard.data_utils import extract_ticker_from_col, fetch_prices_from_yf
from unittest.mock import patch

raw = pd.DataFrame({
  'CLOSE_A':[1,2],
  'CLOSE_B':[3,4]
}, index=pd.date_range('2026-01-01', periods=2))

with patch('risk_dashboard.data_utils.yf.download', return_value=raw):
    df = fetch_prices_from_yf(['CLOSE_A','CLOSE_B'])
    # expect empty because no numeric "close" with ticker tokens -> df empty or duplicates logged
    assert df.empty or df.columns.duplicated().sum() > 0
