# src/ui/gradio_app.py
import json
from pathlib import Path
import pandas as pd
import gradio as gr

from ..config import default_params, DATA_DIR
from ..utils.validators import sanitize_params
from ..sim.core import run_simulation
from ..sim.extended import run_simulation_extended
from ..sim.dynamic import simulate_dynamic_years
from ..utils.viz import plot_summary, plot_years

DATA_DIR = Path(DATA_DIR)

PARAM_SLIDERS = [
    ("USD_Dominanz", 0.0, 1.0, default_params.get("USD_Dominanz", 0.7)),
    ("RMB_Akzeptanz", 0.0, 1.0, default_params.get("RMB_Akzeptanz", 0.2)),
    ("Zugangsresilienz", 0.0, 1.0, default_params.get("Zugangsresilienz", 0.8)),
    ("Sanktions_Exposure", 0.0, 1.0, default_params.get("Sanktions_Exposure", 0.05)),
    ("Alternativnetz_Abdeckung", 0.0, 1.0, default_params.get("Alternativnetz_Abdeckung", 0.5)),
    ("Liquiditaetsaufschlag", 0.0, 1.0, default_params.get("Liquiditaetsaufschlag", 0.03)),
    ("CBDC_Nutzung", 0.0, 1.0, default_params.get("CBDC_Nutzung", 0.5)),
    ("Golddeckung", 0.0, 1.0, default_params.get("Golddeckung", 0.4)),
    ("innovation", 0.0, 1.0, default_params.get("innovation", 0.6)),
    ("fachkraefte", 0.0, 1.0, default_params.get("fachkraefte", 0.7)),
    ("energie", 0.0, 1.0, default_params.get("energie", 0.5)),
    ("stabilitaet", 0.0, 1.0, default_params.get("stabilitaet", 0.9)),
    ("verschuldung", 0.0, 2.0, default_params.get("verschuldung", 0.8)),
    ("demokratie", 0.0, 1.0, default_params.get("demokratie", 0.8)),
    # zusätzliche Parameter, die im config.default_params vorhanden sind
    ("FX_Schockempfindlichkeit", 0.0, 2.0, default_params.get("FX_Schockempfindlichkeit", 0.8)),
    ("Reserven_Monate", 0, 24, default_params.get("Reserven_Monate", 6)),
]

def _load_uploaded_file(uploaded):
    if uploaded is None:
        return None
    # Gradio liefert ein temporäres File-Objekt mit .name Pfad
    path = getattr(uploaded, "name", None) or (uploaded[0] if isinstance(uploaded, (list, tuple)) else None)
    if path is None:
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        try:
            return pd.read_csv(path)
        except Exception:
            return None

def _collect_params_from_values(values):
    keys = [p[0] for p in PARAM_SLIDERS]
    params = {k: float(v) for k, v in zip(keys, values[: len(keys)])}
    return params

def build_demo():
    with gr.Blocks() as demo:
        gr.Markdown("## Makro‑Simulator — interaktive Oberfläche")

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Parameter")
                sliders = {}
                for name, lo, hi, val in PARAM_SLIDERS:
                    step = 0.01 if hi <= 2.0 else 1.0
                    # Reserven_Monate ist integer
                    if name == "Reserven_Monate":
                        sliders[name] = gr.Slider(label=name, minimum=lo, maximum=hi, value=int(val), step=1)
                    else:
                        sliders[name] = gr.Slider(label=name, minimum=lo, maximum=hi, value=float(val), step=0.01)

                gr.Markdown("### Lauf‑Einstellungen")
                N = gr.Number(label="Samples N", value=500, precision=0)
                seed = gr.Number(label="Seed", value=42, precision=0)
                extended_flag = gr.Checkbox(label="Erweitertes Modell (Extended)", value=True)
                save_csv = gr.Checkbox(label="Samples als CSV speichern", value=False)
                csv_name = gr.Textbox(label="CSV Dateiname (optional)", value="samples_run.csv")
                use_chunk = gr.Checkbox(label="Chunking bei großem N", value=True)
                chunk = gr.Number(label="Chunkgröße", value=200, precision=0)

                gr.Markdown("### Kalibrierung / Daten")
                upload_calib = gr.File(label="Kalibrierungsdatei (CSV/Parquet) hochladen", file_count="single")

                gr.Markdown("### Mehrjahres‑Optionen")
                years = gr.Number(label="Jahre (Dynamic)", value=20, precision=0)
                trends_json = gr.Textbox(label="Annual Trends (JSON)", value='{"innovation": 0.01}', lines=2)
                shocks_json = gr.Textbox(label="Shock Events (JSON)", value='[{"year":3,"changes":{"CBDC_Nutzung":0.2}}]', lines=2)

            with gr.Column(scale=3):
                gr.Markdown("### Ergebnisse")
                summary_table = gr.Dataframe(headers=["metric","p05","median","p95"], label="Summary (Quantile)", row_count=10)
                summary_plot = gr.Plot(label="Summary Plot")
                years_table = gr.Dataframe(headers=["Jahr","Importkosten","Resilienz","Volatilität"], label="Mehrjahres‑Tabelle", row_count=20)
                years_plot = gr.Plot(label="Mehrjahres‑Plot")
                csv_output = gr.File(label="CSV Ergebnis (Download)")

        # explizite Callback-Signaturen (weniger fehleranfällig)
        def run_once(
            *slider_vals,
            N_val,
            seed_val,
            extended_val,
            save_csv_val,
            csv_name_val,
            use_chunk_val,
            chunk_val,
            upload_file
        ):
            try:
                params = _collect_params_from_values(slider_vals)
                params = sanitize_params(params)
                n = int(N_val) if N_val is not None else 0
                sd = int(seed_val) if seed_val is not None else 0
                ext = bool(extended_val)
                save_csv_flag = bool(save_csv_val)
                use_chunk_flag = bool(use_chunk_val)
                chunk_size = int(chunk_val) if chunk_val is not None else 200

                calib_df = _load_uploaded_file(upload_file)

                if ext:
                    # return_samples=True so we can get csv_path when save_csv=True
                    csv_or_samples, summary = run_simulation_extended(
                        params,
                        N=n,
                        seed=sd,
                        return_samples=True,
                        save_samples_to_csv=save_csv_flag,
                        csv_name=(csv_name_val or None),
                        use_chunk=(use_chunk_flag and n > 2000),
                        chunk=chunk_size,
                        calibrate_from=calib_df
                    )
                    # if CSV saved, csv_or_samples is Path; else DataFrame
                    if save_csv_flag and isinstance(csv_or_samples, (str, Path)):
                        csv_path = str(csv_or_samples)
                    else:
                        csv_path = None
                else:
                    _, summary = run_simulation(params, N=n, seed=sd, return_samples=False)
                    csv_path = None

                fig = plot_summary(summary)
                # prepare summary dataframe for display
                summary_df = summary.reset_index().rename(columns={"index": "metric"})
                return summary_df, fig, None if csv_path is None else csv_path
            except Exception as e:
                # Rückgabe: leere Tabelle, leeres Plot, kein File; Fehler in Konsole
                return pd.DataFrame(), None, None

        def run_years(
            *slider_vals,
            N_val,
            seed_val,
            extended_val,
            use_chunk_val,
            chunk_val,
            years_val,
            trends_val,
            shocks_val,
            upload_file
        ):
            try:
                params = _collect_params_from_values(slider_vals)
                params = sanitize_params(params)
                n = int(N_val) if N_val is not None else 0
                sd = int(seed_val) if seed_val is not None else 0
                ext = bool(extended_val)
                use_chunk_flag = bool(use_chunk_val)
                chunk_size = int(chunk_val) if chunk_val is not None else 200
                yrs = int(years_val) if years_val is not None else 20

                # parse JSON inputs robust
                try:
                    trends = json.loads(trends_val) if trends_val and trends_val.strip() else {}
                except Exception:
                    trends = {}
                try:
                    shocks = json.loads(shocks_val) if shocks_val and shocks_val.strip() else []
                except Exception:
                    shocks = []

                calib_df = _load_uploaded_file(upload_file)

                df_years = simulate_dynamic_years(
                    params,
                    years=yrs,
                    N=n,
                    seed=sd,
                    extended=ext,
                    annual_trends=trends,
                    shock_events=shocks,
                    clamp=True,
                    use_chunk_for_large_N=use_chunk_flag,
                    chunk=chunk_size,
                    force_csv=False
                )

                fig = plot_years(df_years, title="Mehrjahres‑Simulation")
                return None, fig, df_years
            except Exception as e:
                return None, None, pd.DataFrame()

        # Inputs list: slider components in order + controls
        slider_components = [sliders[name] for name, _, _, _ in PARAM_SLIDERS]
        inputs_run = slider_components + [N, seed, extended_flag, save_csv, csv_name, use_chunk, chunk, upload_calib]
        inputs_years = slider_components + [N, seed, extended_flag, use_chunk, chunk, years, trends_json, shocks_json, upload_calib]

        btn_run = gr.Button("Einmalige Simulation ausführen")
        btn_years = gr.Button("Mehrjahres‑Simulation ausführen")

        btn_run.click(
            fn=run_once,
            inputs=inputs_run,
            outputs=[summary_table, summary_plot, csv_output]
        )

        btn_years.click(
            fn=run_years,
            inputs=inputs_years,
            outputs=[summary_table, years_plot, years_table]
        )

    return demo

demo = build_demo()
