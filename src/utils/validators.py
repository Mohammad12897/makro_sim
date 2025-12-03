import numpy as np
from ..config import default_params
def clamp01(x):
    try: return float(np.clip(x, 0.0, 1.0))
    except Exception: return np.nan
def merge_with_defaults(params):
    out = default_params.copy(); out.update(params or {}); return out
def sanitize_params(p: dict, allow_0_2_for_verschuldung=True):
    p = merge_with_defaults(p or {})
    for k in ["USD_Dominanz","RMB_Akzeptanz","Zugangsresilienz","Sanktions_Exposure","Alternativnetz_Abdeckung","Liquiditaetsaufschlag","CBDC_Nutzung","Golddeckung"]:
        p[k] = clamp01(p.get(k, default_params.get(k, 0.0)))
    try: fx = float(p.get("FX_Schockempfindlichkeit", default_params.get("FX_Schockempfindlichkeit", 0.8)))
    except Exception: fx = default_params.get("FX_Schockempfindlichkeit", 0.8)
    p["FX_Schockempfindlichkeit"] = float(np.clip(fx, 0.0, 2.0))
    try: p["Reserven_Monate"] = int(np.clip(int(p.get("Reserven_Monate", default_params["Reserven_Monate"])), 0, 24))
    except Exception: p["Reserven_Monate"] = default_params["Reserven_Monate"]
    p["innovation"]  = clamp01(p.get("innovation", 0.6)); p["fachkraefte"] = clamp01(p.get("fachkraefte", 0.7))
    p["energie"]     = clamp01(p.get("energie", 0.5)); p["stabilitaet"] = clamp01(p.get("stabilitaet", 0.9))
    try: v = float(p.get("verschuldung", 0.8))
    except Exception: v = 0.8
    v = np.clip(v, 0.0, 2.0); p["verschuldung"] = float(v) if allow_0_2_for_verschuldung else float(v / 2.0)
    p["demokratie"] = clamp01(p.get("demokratie", default_params.get("demokratie", 0.8)))
    return p
