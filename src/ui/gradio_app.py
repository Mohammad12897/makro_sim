# src/ui/gradio_app.py
import gradio as gr
import pandas as pd
from ..config import default_params
from ..sim.core import run_simulation
from ..sim.extended import run_simulation_extended
from ..sim.dynamic import simulate_dynamic_years
from ..utils.viz import plot_summary, plot_years
from ..utils.validators import sanitize_params

PARAM_SLIDERS = [
    ("USD_Dominanz", 0.0, 1.0, 0.7),
    ("RMB_Akzeptanz", 0.0, 1.0, 0.2),
    ("Zugangsresilienz", 0.0, 1.0, 0.8),
    ("Sanktions_Exposure", 0.0, 1.0, 0.05),
    ("Alternativnetz_Abdeckung", 0.0, 1.0, 0.5),
    ("Liquiditaetsaufschlag", 0.0, 1.0, 0.03),
    ("CBDC_Nutzung", 0.0, 1.0, 0.5),
    ("Golddeckung", 0.0, 1.0, 0.4),
    ("innovation", 0.0, 1.0, 0.6),
    ("fachkraefte", 0.0, 1.0, 0.7),
    ("energie", 0.0, 1.0, 0.5),
    ("stabilitaet", 0.0, 1.0, 0.9),
    ("verschuldung", 0.0, 2.0, 0.8),
    ("demokratie", 0.0, 1.0, 0.8),
]

def build_demo():
    with gr.Blocks() as demo:
        gr.Markdown("## Makro‑Simulator")
        with gr.Row():
            with gr.Column(scale=2):
                sliders = {}
                for name, lo, hi, val in PARAM_SLIDERS:
                    sliders[name] = gr.Slider(label=name, minimum=lo, maximum=hi, value=val, step=0.01)
                N = gr.Number(label="Samples N", value=200, precision=0)
                seed = gr.Number(label="Seed", value=42, precision=0)
                extended = gr.Checkbox(label="Erweitertes Modell", value=True)
                use_chunk = gr.Checkbox(label="Chunking bei großem N", value=True)
                chunk = gr.Number(label="Chunkgröße", value=100, precision=0)
                years = gr.Number(label="Jahre (dynamische Simulation)", value=20, precision=0)
                trends_json = gr.Textbox(label="Annual Trends (JSON)", value='{"innovation": 0.01}', lines=2)
                shocks_json = gr.Textbox(label="Shock Events (JSON)", value='[{"year":3,"changes":{"CBDC_Nutzung":0.2}}]', lines=2)

            with gr.Column(scale=3):
                summary_plot = gr.Plot(label="Summary")
                years_plot = gr.Plot(label="Mehrjahres‑Simulation")
                table = gr.Dataframe(headers=["Jahr","Importkosten","Resilienz","Volatilität"], row_count=20)

        def run_once(*vals):
            keys = [x[0] for x in PARAM_SLIDERS]
            params = {k: float(v) for k, v in zip(keys, vals[:len(keys)])}
            n = int(vals[len(keys)])
            sd = int(vals[len(keys)+1])
            ext = bool(vals[len(keys)+2])
            chunk_flag = bool(vals[len(keys)+3])
            chunk_size = int(vals[len(keys)+4])
            p = sanitize_params(params)
            if ext:
                _, summary = run_simulation_extended(p, N=n, seed=sd, return_samples=False,
                                                     use_chunk=(chunk_flag and n > 2000), chunk=chunk_size)
            else:
                _, summary = run_simulation(p, N=n, seed=sd, return_samples=False)
            fig = plot_summary(summary)
            return fig

        def run_years(*vals):
            idx = len(PARAM_SLIDERS)
            keys = [x[0] for x in PARAM_SLIDERS]
            params = {k: float(vals[i]) for i, k in enumerate(keys)}
            n = int(vals[idx]); sd = int(vals[idx+1]); ext = bool(vals[idx+2])
            chunk_flag = bool(vals[idx+3]); chunk_size = int(vals[idx+4])
            yrs = int(vals[idx+5])
            try:
                trends = pd.io.json.loads(vals[idx+6]) if vals[idx+6] else {}
            except Exception:
                trends = {}
            try:
                shocks = pd.io.json.loads(vals[idx+7]) if vals[idx+7] else []
            except Exception:
                shocks = []
            df = simulate_dynamic_years(params, years=yrs, N=n, seed=sd, extended=ext,
                                        annual_trends=trends, shock_events=shocks,
                                        use_chunk_for_large_N=chunk_flag, chunk=chunk_size)
            fig = plot_years(df, title="Mehrjahres‑Simulation")
            return fig, df

        btn_summary = gr.Button("Einmalige Simulation ausführen")
        btn_years = gr.Button("Mehrjahres‑Simulation ausführen")

        inputs = list(sliders.values()) + [N, seed, extended, use_chunk, chunk, years, trends_json, shocks_json]
        btn_summary.click(run_once, inputs=inputs[:-2], outputs=[summary_plot])
        btn_years.click(run_years, inputs=inputs, outputs=[years_plot, table])

    return demo

demo = build_demo()
