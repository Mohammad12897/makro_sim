#tests/test_covariance.py
from core.portfolio_sim.covariance import build_asset_covariance

def test_covariance_shape():
    cov = build_asset_covariance()
    assert cov.shape == (3, 3)
    assert all(cov.columns == ["equity", "bonds", "gold"])
