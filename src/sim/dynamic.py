from .extended import run_simulation_extended
from .extended import run_simulation_extended
from .core import run_simulation
from ..utils.validators import sanitize_params
import pandas as pd

PRESET_SCENARIOS = {"Baseline (keine Trends)": {"annual_trends": {}, "shock_events": []}}

def simulate_dynamic_years(
    params,
    years=20,
    N=200,
    seed=42,
    extended=False,
    annual_trends=None,
    shock_events=None,
    clamp=True,
    allow_0_2_for_verschuldung=True,
    use_chunk_for_large_N=True,
    chunk=100,
    force_csv=False
):
    annual_trends = annual_trends or {}
    shock_events = shock_events or []
    shocks_by_year = {
        int(e["year"]): e["changes"]
        for e in shock_events
        if isinstance(e, dict) and "year" in e and "changes" in e
    }

    results = []
    p = params.copy() if isinstance(params, dict) else dict(params)

    for year in range(1, int(years) + 1):
        # apply annual trends
        for k, delta in annual_trends.items():
            p[k] = float(p.get(k, 0.0)) + float(delta)

        # apply shock events for this year
        if year in shocks_by_year:
            for k, delta in shocks_by_year[year].items():
                p[k] = float(p.get(k, 0.0)) + float(delta)

        # sanitize parameters
        if clamp:
            p = sanitize_params(p, allow_0_2_for_verschuldung=allow_0_2_for_verschuldung)

        local_seed = int(seed) + year

        if extended:
            use_csv = (int(N) > 5000) or bool(force_csv)
            use_chunk = (use_chunk_for_large_N and int(N) > 2000)
            _, summary = run_simulation_extended(
                p,
                N=N,
                seed=local_seed,
                return_samples=False,
                use_chunk=use_chunk,
                chunk=chunk,
                save_samples_to_csv=use_csv,
                csv_name=f"dyn_seed{local_seed}_year{year}.csv" if use_csv else None
            )
        else:
            _, summary = run_simulation(p, N=N, seed=local_seed, return_samples=False)

        # robust access to summary values
        def _get_median(idx_name):
            try:
                return float(summary.at[idx_name, "median"])
            except Exception:
                try:
                    return float(summary.loc[idx_name, "median"])
                except Exception:
                    return float("nan")

        importkosten = _get_median("importkosten_mult")
        resilienz = _get_median("netto_resilienz")
        volatilitaet = _get_median("system_volatilitaet")

        results.append({
            "Jahr": year,
            "Importkosten": importkosten,
            "Resilienz": resilienz,
            "Volatilität": volatilitaet
        })

    return pd.DataFrame(results)
