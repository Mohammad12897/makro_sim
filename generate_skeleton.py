#!/usr/bin/env python3
from pathlib import Path
import textwrap, os

ROOT = Path.cwd()
SRC = ROOT / "src"
MODULES = ["etl","sim","ui","utils","tests"]
FILES = {
"src/config.py": '''from pathlib import Path
DATA_DIR = Path("/content/drive/MyDrive/makro_sim/data/indicators")
DATA_DIR.mkdir(parents=True, exist_ok=True)
default_params = {
    "USD_Dominanz": 0.7, "RMB_Akzeptanz": 0.2, "Zugangsresilienz": 0.8,
    "Reserven_Monate": 6, "FX_Schockempfindlichkeit": 0.8, "Sanktions_Exposure": 0.05,
    "Alternativnetz_Abdeckung": 0.5, "Liquiditaetsaufschlag": 0.03, "CBDC_Nutzung": 0.5,
    "Golddeckung": 0.4, "innovation": 0.6, "fachkraefte": 0.7, "energie": 0.5,
    "stabilitaet": 0.9, "verschuldung": 0.8, "demokratie": 0.8,
    "country_iso": "DE", "reporter_code": "276"
}
''',
"src/etl/__init__.py": '\"\"\"ETL package\"\"\"',
"src/etl/fetchers.py": '''import pandas as pd, numpy as np
from datetime import datetime
class DataAPI:
    def __init__(self, country_iso="DE", reporter_code="276"):
        self.country_iso = country_iso
        self.reporter_code = reporter_code
    def get_central_bank_reserves(self, start="2015-01"):
        rng = pd.date_range(start, datetime.today(), freq="ME")
        reserves = np.linspace(200e9, 250e9, len(rng))
        return pd.DataFrame({"ts": rng, "reserves_usd": reserves})
    def get_monthly_imports(self, start_year=2015):
        dates, values = [], []
        end_year = datetime.today().year
        for y in range(int(start_year), end_year+1):
            for m in range(1,13):
                ts = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(1)
                dates.append(ts); values.append(1e11 + 2e10 * np.sin(m/12 * np.pi))
        df = pd.DataFrame({"ts": dates, "imports_usd": values})
        return df
    def get(self, name, **kwargs):
        if name == "central_bank_reserves": return self.get_central_bank_reserves(**kwargs)
        if name == "monthly_imports": return self.get_monthly_imports(**kwargs)
        raise ValueError(name)
''',
"src/etl/persistence.py": '''import pandas as pd
from ..config import DATA_DIR
def _write_parquet(df, name):
    path = DATA_DIR / f"{name}.parquet"
    try: df.to_parquet(path, index=False)
    except Exception: df.to_csv(path.with_suffix(".csv"), index=False)
    return path
def store_indicator(name, series, source, quality_flag="ok"):
    df = pd.DataFrame({"indicator_name": name, "value": series.values, "ts": series.index.astype("datetime64[ns]"), "source": source, "quality_flag": quality_flag})
    path = DATA_DIR / f"{name}.parquet"
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df]).drop_duplicates(subset=["ts"]).sort_values("ts")
        except Exception:
            pass
    _write_parquet(df, name)
    return path
''',
"src/etl/transforms.py": '''import pandas as pd, numpy as np
from .fetchers import DataAPI
from .persistence import store_indicator
def fetch_reserves(api: DataAPI):
    cb = api.get("central_bank_reserves"); imp = api.get("monthly_imports")
    def normalize(df, value_col):
        if not isinstance(df, pd.DataFrame): df = pd.DataFrame(df)
        if "ts" not in df.columns: df.rename(columns={df.columns[0]:"ts"}, inplace=True)
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=["ts", value_col]).sort_values("ts")
        return df.set_index("ts").resample("M").last()
    df_res = normalize(cb, "reserves_usd"); df_imp = normalize(imp, "imports_usd")
    df = df_res.join(df_imp, how="inner")
    denom = np.maximum(1.0, df["imports_usd"].values)
    s = pd.Series(df["reserves_usd"].values / denom, index=df.index)
    flag = "ok" if len(s)>0 else "empty"
    path = store_indicator("Reserven_Monate", s, source="CB_API", quality_flag=flag)
    return s, path, flag
''',
"src/sim/core.py": '''import numpy as np, pandas as pd, gc
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
''',
"src/sim/extended.py": '''import numpy as np, pandas as pd, gc
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

def run_simulation_extended(params, N=200, seed=0, return_samples=False,
                            use_chunk=None, chunk=50,
                            save_samples_to_csv=False, csv_name=None):
    """
    Generate N samples for importkosten_mult, netto_resilienz, system_volatilitaet.
    If save_samples_to_csv is True, samples are appended to CSV in DATA_DIR and
    the function returns (csv_path, summary) when return_samples=True or (csv_path, summary) otherwise.
    If return_samples=True and save_samples_to_csv=False, returns (samples_df, summary).
    """
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
        # ensure header will be written on first chunk
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

    # If no samples were generated (N == 0)
    if len(imp_parts) == 0 and not save_samples_to_csv:
        empty = pd.DataFrame(index=["importkosten_mult","netto_resilienz","system_volatilitaet"],
                             data={"p05":[float("nan")]*3,"median":[float("nan")]*3,"p95":[float("nan")]*3})
        if return_samples:
            return pd.DataFrame(columns=["importkosten_mult","netto_resilienz","system_volatilitaet"]), empty
        return None, empty

    # If samples were stored in memory, concatenate
    if not save_samples_to_csv:
        imp_all = np.concatenate(imp_parts).astype(np.float32)
        res_all = np.concatenate(res_parts).astype(np.float32)
        vola_all = np.concatenate(vola_parts).astype(np.float32)
    else:
        # read back CSV to compute summary in a memory-efficient way using chunks
        csv_path = Path(csv_path) if csv_path is not None else None
        if csv_path is None or not csv_path.exists():
            # fallback: no CSV present
            imp_all = np.array([], dtype=np.float32)
            res_all = np.array([], dtype=np.float32)
            vola_all = np.array([], dtype=np.float32)
        else:
            # compute percentiles by streaming through CSV in chunks
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

    # compute percentiles and summary
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
            # return csv path and summary
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

''',
"src/sim/dynamic.py": '''from .extended import run_simulation_extended
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
''',
"src/utils/validators.py": '''import numpy as np
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
''',
"src/utils/viz.py": '''import matplotlib.pyplot as plt
import pandas as pd
def plot_summary(summary: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6,3))
    df_plot = summary[["p05","median","p95"]].transpose()
    df_plot.plot(kind="bar", ax=ax, color=["#82B1FF","#2962FF","#0039CB"])
    ax.set_title("Makro-Metriken p05 / median / p95"); ax.set_ylabel("Wert")
    plt.tight_layout(); plt.close(fig); return fig
def plot_years(df, title="Mehrjahres-Simulation"):
    fig, ax = plt.subplots(figsize=(8,4)); df_plot = df.set_index("Jahr"); df_plot.plot(ax=ax, marker="o")
    ax.set_title(title); ax.set_ylabel("Wert"); ax.grid(alpha=0.3); plt.tight_layout(); plt.close(fig); return fig
''',
"src/ui/gradio_app.py": '''import gradio as gr
from ..config import default_params
from ..etl.fetchers import DataAPI
from ..etl.transforms import fetch_reserves
def build_demo():
    with gr.Blocks() as demo:
        gr.Markdown("## Makro-Simulator Platzhalter UI")
        btn = gr.Button("Test Daten laden"); out = gr.Textbox()
        def _test():
            api = DataAPI(); s, path, flag = fetch_reserves(api)
            return f"Reserven_Monate: {s.iloc[-1]:.2f} (flag={flag})"
        btn.click(_test, inputs=[], outputs=[out])
    return demo
demo = build_demo()
''',
"src/tests/test_etl.py": '''from src.etl.fetchers import DataAPI
from src.etl.transforms import fetch_reserves
def test_fetch_reserves_basic():
    api = DataAPI(); s, path, flag = fetch_reserves(api)
    assert len(s) > 0
''',
"run.py": '''from src.ui.gradio_app import demo
if __name__ == "__main__":
    demo.launch(share=True)
'''
}

def ensure_dirs():
    SRC.mkdir(exist_ok=True)
    for m in MODULES:
        (SRC / m).mkdir(parents=True, exist_ok=True)

def write_files():
    for rel, content in FILES.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists(): print("skip", path); continue
        with open(path, "w", encoding="utf-8") as f: f.write(textwrap.dedent(content))
        print("created", path)

def main():
    ensure_dirs(); write_files(); print("skeleton created")

if __name__ == "__main__":
    main()
