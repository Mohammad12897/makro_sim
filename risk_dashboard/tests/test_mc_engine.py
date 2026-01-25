#tests/test_mc_engine.py
import numpy as np
from core.portfolio_sim.mc_engine import run_portfolio_mc
from core.utils import load_presets


def test_mc_engine_runs():
    presets = load_presets()
    land = list(presets.keys())[0]

    sim, summary = run_portfolio_mc(
        land=land,
        presets=presets,
        w_equity=50,
        w_bond=30,
        w_gold=20,
        years=5,
        scenario_name="Keins"
    )

    assert "paths" in sim
    assert "terminal_distribution" in sim
    assert len(summary) == 5
