# scripts/test_checks.py
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
import re
import inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from risk_dashboard.core.etf_tools import get_etf_candidates_for_index

def test_get_etf_candidates_for_index_empty():
    df = get_etf_candidates_for_index("NON_EXISTENT_INDEX")
    assert isinstance(df, pd.DataFrame)
    expected_cols = {"ticker","name","domicile","expense_ratio","aum","replication"}
    assert expected_cols.issubset(set(df.columns))
