# Datei: /src/tests/test_integration_real.py
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

def test_etl_and_simulation_end_to_end(tmp_path, monkeypatch):
    # setze DATA_DIR auf temporären Ordner
    from src import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    api = MockAPI()
    s, path, flag = fetch_reserves(api)
    assert flag in ("ok", "empty")
    assert hasattr(s, "shape") or s is None

    params = default_params.copy()
    if s is not None and len(s) > 0:
        params["Reserven_Monate"] = int(round(float(s.iloc[-1])))

    # kleiner In‑Memory Lauf
    samples, summary = run_simulation_extended(params, N=100, seed=123, return_samples=True)
    assert "importkosten_mult" in summary.index
    assert "median" in summary.columns

    # CSV Streaming in tmp_path
    csv_name = "test_integration_samples.csv"
    csv_path, summary2 = run_simulation_extended(
        params,
        N=200,
        seed=124,
        return_samples=True,
        save_samples_to_csv=True,
        csv_name=csv_name
    )
    assert Path(csv_path).exists()
    df_csv = pd.read_csv(csv_path)
    assert set(["importkosten_mult","netto_resilienz","system_volatilitaet"]).issubset(df_csv.columns)
    assert len(df_csv) > 0
