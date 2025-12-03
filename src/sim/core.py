import numpy as np, pandas as pd, gc
from ..utils.validators import sanitize_params
def run_simulation(params, N=200, seed=0, return_samples=False):
    rng = np.random.default_rng(int(seed)); p = sanitize_params(params)
    base_import = 1.0 + 0.6*p["USD_Dominanz"] + 0.5*p["Liquiditaetsaufschlag"] - 0.3*p["CBDC_Nutzung"]
    base_resil  = 0.5 + 0.5*p["Golddeckung"] + 0.3*p["Alternativnetz_Abdeckung"] + 0.1*p["CBDC_Nutzung"]
    base_vola   = 0.03 + 0.08*p["FX_Schockempfindlichkeit"] + 0.05*(1-p["Zugangsresilienz"])
    imp  = rng.normal(loc=base_import, scale=0.05, size=int(N)).astype(np.float32)
    res  = rng.normal(loc=base_resil,  scale=0.03, size=int(N)).astype(np.float32)
    vola = rng.normal(loc=base_vola,   scale=0.02, size=int(N)).astype(np.float32)
    samples = pd.DataFrame({"importkosten_mult": imp, "netto_resilienz": res, "system_volatilitaet": vola})
    summary = samples.quantile([0.05,0.5,0.95]).T; summary.columns = ["p05","median","p95"]
    if return_samples: return samples, summary
    del imp, res, vola; gc.collect()
    return None, summary
