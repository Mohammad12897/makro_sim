# src/tests/test_sim.py
import numpy as np
import pandas as pd
from src.sim.core import run_simulation
from src.sim.extended import run_simulation_extended
from src.sim.dynamic import simulate_dynamic_years
from src.utils.validators import sanitize_params
from src.config import default_params

def test_core_summary_shape():
    _, summary = run_simulation(default_params, N=200, seed=0, return_samples=False)
    assert list(summary.columns) == ["p05","median","p95"]
    assert set(summary.index) == {"importkosten_mult","netto_resilienz","system_volatilitaet"}

def test_extended_chunking_consistency():
    p = sanitize_params(default_params)
    samples_a, summary_a = run_simulation_extended(p, N=1000, seed=123, return_samples=True, use_chunk=False)
    samples_b, summary_b = run_simulation_extended(p, N=1000, seed=123, return_samples=True, use_chunk=True, chunk=100)
    # gleiche Seed -> statistisch sehr ähnlich; median‑Differenzen klein
    diff = (summary_a["median"] - summary_b["median"]).abs()
    assert (diff < 1e-2).all()
    assert len(samples_b) == 1000

def test_dynamic_years_baseline_length():
    df = simulate_dynamic_years(default_params, years=10, N=500, seed=42, extended=True)
    assert len(df) == 10
    assert set(["Jahr","Importkosten","Resilienz","Volatilität"]).issubset(df.columns)

def test_dynamic_trends_and_shocks():
    trends = {"innovation": 0.01, "verschuldung": 0.05}
    shocks = [{"year": 3, "changes": {"CBDC_Nutzung": 0.2}}, {"year": 7, "changes": {"Golddeckung": -0.1}}]
    df = simulate_dynamic_years(default_params, years=10, N=300, seed=7, extended=True,
                                annual_trends=trends, shock_events=shocks)
    assert pd.notnull(df.loc[df["Jahr"] == 3, "Resilienz"]).all()

