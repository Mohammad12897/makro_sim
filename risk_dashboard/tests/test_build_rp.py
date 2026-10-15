# tests/test_build_rp.py
import pandas as pd
from unittest.mock import patch
from risk_dashboard.core.investment_engine import build_regime_risk_parity_portfolio

def test_build_regime_risk_parity_portfolio_basic():
    low = ["AGGG.L"]
    medium = ["IMEU.L"]
    high = ["CSPX.L"]

    # Mock load_etf_prices inside the module that calls it (patch target depends on import path)
    sample_prices = pd.DataFrame({
        "AGGG.L": [100, 101],
        "IMEU.L": [50, 51],
        "CSPX.L": [200, 202],
    }, index=pd.date_range("2025-10-01", periods=2))

    with patch("risk_dashboard.core.investment_engine.load_etf_prices", return_value=sample_prices):
        rp_struct, rets, missing = build_regime_risk_parity_portfolio(low, medium, high, period="2d")
        assert "Low" in rp_struct and "Medium" in rp_struct and "High" in rp_struct
        assert not rets.empty
        assert missing == []  # oder nur die tatsächlich fehlenden