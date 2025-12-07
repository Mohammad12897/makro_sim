# src/tests/test_sim_quick.py
import pandas as pd
from pathlib import Path
from src.sim.extended import run_simulation_extended
from src.sim.dynamic import simulate_dynamic_years
from src.config import default_params

def test_extended_small_inmemory(tmp_path, monkeypatch):
    # isolate DATA_DIR
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    params = default_params.copy()
    samples, summary = run_simulation_extended(params, N=50, seed=1, return_samples=True, save_samples_to_csv=False)
    assert isinstance(samples, pd.DataFrame)
    assert "importkosten_mult" in summary.index

def test_dynamic_small(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    params = default_params.copy()
    df_years = simulate_dynamic_years(params, years=5, N=100, seed=2, extended=True, annual_trends={"innovation":0.01}, shock_events=[])
    assert df_years.shape[0] == 5
    assert "Importkosten" in df_years.columns

