# tests/test_fetch_prices.py
import pandas as pd
from unittest.mock import patch
from risk_dashboard.data_utils import fetch_prices_from_yf, extract_ticker_from_col

def test_fetch_flatten_and_normalize():
    # prepare a MultiIndex-like raw returned by yf.download
    mi = pd.MultiIndex.from_tuples([('Adj Close','CSPX.L'),('Adj Close','AGGG.L')])
    raw = pd.DataFrame([[1,2],[3,4]], index=pd.date_range('2026-01-01', periods=2), columns=mi)

    with patch('risk_dashboard.data_utils.yf.download', return_value=raw):
        df = fetch_prices_from_yf(['CSPX.L','AGGG.L'])
        assert list(df.columns) == ['CSPX.L','AGGG.L']

def test_fetch_handles_delisted():
    # simulate yf.download returning empty DataFrame
    with patch('risk_dashboard.data_utils.yf.download', return_value=pd.DataFrame()):
        df = fetch_prices_from_yf(['CLOSE_A','CLOSE_B'])
        assert df.empty
