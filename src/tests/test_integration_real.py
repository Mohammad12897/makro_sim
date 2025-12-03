# src/tests/test_integration_real.py
import pytest
from src.etl.transforms import fetch_reserves
from src.config import default_params
from src.sim.extended import run_simulation_extended
from pathlib import Path
import pandas as pd

class MockAPI:
    """
    Einfacher Mock der DataAPI für Tests.
    Liefert kleine DataFrames für central_bank_reserves und monthly_imports.
    """
    def get(self, key):
        if key == "central_bank_reserves":
            return pd.DataFrame({
                "ts": ["2020-01-31", "2020-02-29"],
                "reserves_usd": [100.0, 110.0]
            })
        if key == "monthly_imports":
            return pd.DataFrame({
                "ts": ["2020-01-31", "2020-02-29"],
                "imports_usd": [50.0, 55.0]
            })
        return []

def test_etl_and_simulation_end_to_end(tmp_path):
    # ETL: benutze MockAPI statt realer API
    api = MockAPI()
    s, path, flag = fetch_reserves(api)  # kein use_comtrade Keyword nötig
    assert flag in ("ok", "empty")
    assert hasattr(s, "shape") or s is None

    # build params
    params = default_params.copy()
    if s is not None and len(s) > 0:
        params["Reserven_Monate"] = int(round(float(s.iloc[-1])))

    # run a small simulation (in-memory)
    samples, summary = run_simulation_extended(params, N=200, seed=123, return_samples=True)
    assert "importkosten_mult" in summary.index
    assert "median" in summary.columns

    # run a CSV streaming run (small) to ensure path creation
    csv_path, summary2 = run_simulation_extended(
        params,
        N=500,
        seed=124,
        return_samples=True,
        save_samples_to_csv=True,
        csv_name="test_integration_samples.csv"
    )
    assert Path(csv_path).exists()
    assert "median" in summary2.columns
