# src/sim/extended.py
import time
import gc
from pathlib import Path
import numpy as np
import pandas as pd
from ..utils.validators import sanitize_params
from ..config import DATA_DIR

def _compute_bases_extended(p):
    base_import = 1.0 + 0.6*p["USD_Dominanz"] + 0.5*p["Liquiditaetsaufschlag"] - 0.3*p["CBDC_Nutzung"]
    base_resil  = 0.5 + 0.5*p["Golddeckung"] + 0.3*p["Alternativnetz_Abdeckung"] + 0.1*p["CBDC_Nutzung"]
    base_vola   = 0.03 + 0.08*p["FX_Schockempfindlichkeit"] + 0.05*(1-p["Zugangsresilienz"])
    base_import += 0.4*(1-p.get("innovation",0.6))
    base_resil  += 0.3*p.get("fachkraefte",0.7) + 0.2*p.get("stabilitaet",0.9)
    base_vola   += 0.05*p.get("energie",0.5) + 0.05*p.get("verschuldung",0.8)
    d = p.get("demokratie", 0.8)
    base_resil += 0.25 * d
    base_vola  = max(0.0, base_vola - 0.02 * d)
    base_import = max(0.0, base_import - 0.05 * d)
    base_import -= 0.2 * p.get("innovation",0.6) * d
    base_resil  += 0.15 * p.get("fachkraefte",0.7) * d
    base_import = max(0.0, base_import); base_resil = max(0.0, base_resil); base_vola = max(0.0, base_vola)
    return base_import, base_resil, base_vola

def _calibrate_from_series(calibrate_from):
    """
    Erwartet eine pandas.Series oder DataFrame mit numeric Werten.
    Liefert einen dict mit abgeleiteten Parameter-Anpassungen, z.B. Reserven-Monate.
    """
    if calibrate_from is None:
        return {}
    if isinstance(calibrate_from, pd.DataFrame):
        # nehme erste numerische Spalte
        ser = calibrate_from.select_dtypes("number").iloc[:,0]
    elif isinstance(calibrate_from, pd.Series):
        ser = calibrate_from
    else:
        try:
            ser = pd.Series(calibrate_from)
        except Exception:
            return {}
    ser = ser.dropna()
    if ser.empty:
        return {}
    median = float(ser.median())
    mean = float(ser.mean())
    # Beispielableitung: Reserven_Monate aus Median (gerundet)
    return {"Reserven_Monate": int(round(median)), "Reserven_Monate_mean": float(mean)}

def run_simulation_extended(params, N=200, seed=0, return_samples=False,
                            use_chunk=None, chunk=50,
                            save_samples_to_csv=False, csv_name=None,
                            calibrate_from=None):
    """
    Erweiterte Simulation mit optionaler Kalibrierung.
    - calibrate_from: pandas.Series/DataFrame oder Pfad zu Parquet/CSV; wenn gesetzt, werden Parameter abgeleitet.
    Rückgabe:
      - wenn return_samples=True und save_samples_to_csv=False: (samples_df, summary)
      - wenn return_samples=True und save_samples_to_csv=True: (csv_path, summary)
      - sonst: (None, summary)
    """
    # optional: Kalibrierung anwenden
    if calibrate_from is not None:
        if isinstance(calibrate_from, (str, Path)):
            try:
                dfc = pd.read_parquet(str(calibrate_from))
            except Exception:
                try:
                    dfc = pd.read_csv(str(calibrate_from))
                except Exception:
                    dfc = None
            calib = _calibrate_from_series(dfc)
        else:
            calib = _calibrate_from_series(calibrate_from)
        if calib:
            params = params.copy()
            params.update(calib)

    rng = np.random.default_rng(int(seed))
    p = sanitize_params(params)
    base_import, base_resil, base_vola = _compute_bases_extended(p)
    N = int(max(0, N))
    use_chunk = (use_chunk if use_chunk is not None else (N > 2000))
    chunk = int(max(1, chunk))
    csv_path = None

    if save_samples_to_csv:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if csv_name is None:
            csv_name = f"samples_ext_seed{int(seed)}_N{N}_{int(time.time())}.csv"
        csv_path = Path(DATA_DIR) / csv_name
        if csv_path.exists():
            csv_path.unlink()

    imp_parts = []
    res_parts = []
    vola_parts = []
    generated = 0
    first_chunk = True

    if use_chunk and N > 0:
        while generated < N:
            m = min(chunk, N - generated)
            imp = rng.normal(loc=base_import, scale=0.05, size=m).astype(np.float32)
            res = rng.normal(loc=base_resil,  scale=0.03, size=m).astype(np.float32)
            vola = rng.normal(loc=base_vola,   scale=0.02, size=m).astype(np.float32)
            vola = np.clip(vola, 0.0, None)

            if save_samples_to_csv:
                df_chunk = pd.DataFrame({
                    "importkosten_mult": imp,
                    "netto_resilienz": res,
                    "system_volatilitaet": vola
                })
                df_chunk.to_csv(csv_path, mode="a", index=False, header=first_chunk)
                first_chunk = False
                del df_chunk
            else:
                imp_parts.append(imp); res_parts.append(res); vola_parts.append(vola)

            generated += m

    else:
        if N > 0:
            imp = rng.normal(loc=base_import, scale=0.05, size=N).astype(np.float32)
            res = rng.normal(loc=base_resil,  scale=0.03, size=N).astype(np.float32)
            vola = rng.normal(loc=base_vola,   scale=0.02, size=N).astype(np.float32)
            vola = np.clip(vola, 0.0, None)
            if save_samples_to_csv:
                df = pd.DataFrame({
                    "importkosten_mult": imp,
                    "netto_resilienz": res,
                    "system_volatilitaet": vola
                })
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                df.to_csv(Path(DATA_DIR) / (csv_name or "samples.csv"), index=False)
                del df
            else:
                imp_parts.append(imp); res_parts.append(res); vola_parts.append(vola)

    if len(imp_parts) == 0 and not save_samples_to_csv:
        empty = pd.DataFrame(index=["importkosten_mult","netto_resilienz","system_volatilitaet"],
                             data={"p05":[float("nan")]*3,"median":[float("nan")]*3,"p95":[float("nan")]*3})
        if return_samples:
            return pd.DataFrame(columns=["importkosten_mult","netto_resilienz","system_volatilitaet"]), empty
        return None, empty

    if not save_samples_to_csv:
        imp_all = np.concatenate(imp_parts).astype(np.float32)
        res_all = np.concatenate(res_parts).astype(np.float32)
        vola_all = np.concatenate(vola_parts).astype(np.float32)
    else:
        csv_path = Path(csv_path) if csv_path is not None else None
        if csv_path is None or not csv_path.exists():
            imp_all = np.array([], dtype=np.float32)
            res_all = np.array([], dtype=np.float32)
            vola_all = np.array([], dtype=np.float32)
        else:
            imp_vals = []
            res_vals = []
            vola_vals = []
            for chunk_df in pd.read_csv(csv_path, chunksize=100000):
                imp_vals.append(chunk_df["importkosten_mult"].to_numpy(dtype=np.float32))
                res_vals.append(chunk_df["netto_resilienz"].to_numpy(dtype=np.float32))
                vola_vals.append(chunk_df["system_volatilitaet"].to_numpy(dtype=np.float32))
            imp_all = np.concatenate(imp_vals) if len(imp_vals) else np.array([], dtype=np.float32)
            res_all = np.concatenate(res_vals) if len(res_vals) else np.array([], dtype=np.float32)
            vola_all = np.concatenate(vola_vals) if len(vola_vals) else np.array([], dtype=np.float32)

    q05 = (np.percentile(imp_all,5) if imp_all.size else float("nan"),
           np.percentile(res_all,5) if res_all.size else float("nan"),
           np.percentile(vola_all,5) if vola_all.size else float("nan"))
    q50 = (np.percentile(imp_all,50) if imp_all.size else float("nan"),
           np.percentile(res_all,50) if res_all.size else float("nan"),
           np.percentile(vola_all,50) if vola_all.size else float("nan"))
    q95 = (np.percentile(imp_all,95) if imp_all.size else float("nan"),
           np.percentile(res_all,95) if res_all.size else float("nan"),
           np.percentile(vola_all,95) if vola_all.size else float("nan"))

    summary = pd.DataFrame({
        "p05":[q05[0],q05[1],q05[2]],
        "median":[q50[0],q50[1],q50[2]],
        "p95":[q95[0],q95[1],q95[2]]
    }, index=["importkosten_mult","netto_resilienz","system_volatilitaet"])

    if return_samples:
        if save_samples_to_csv:
            return csv_path, summary
        samples = pd.DataFrame({
            "importkosten_mult": imp_all,
            "netto_resilienz": res_all,
            "system_volatilitaet": vola_all
        })
        del imp_parts, res_parts, vola_parts, imp_all, res_all, vola_all
        gc.collect()
        return samples, summary

    del imp_parts, res_parts, vola_parts, imp_all, res_all, vola_all
    gc.collect()
    return None, summary
