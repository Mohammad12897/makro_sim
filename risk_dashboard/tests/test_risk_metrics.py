import numpy as np
from core.portfolio_sim.risk_metrics import mc_risk_metrics


def test_risk_metrics_basic():
    sim = {
        "paths": np.array([
            [1.0, 1.1, 1.2],
            [1.0, 0.9, 1.0],
            [1.0, 1.05, 1.1],
        ]),
        "terminal_distribution": np.array([1.2, 1.0, 1.1])
    }

    metrics = mc_risk_metrics(sim)

    assert metrics["mean"] > 0
    assert metrics["std"] >= 0
    assert "sharpe" in metrics
    assert "var95" in metrics
    assert "cvar95" in metrics
    assert "max_drawdown" in metrics
