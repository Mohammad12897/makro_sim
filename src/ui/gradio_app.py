# src/ui/gradio_app.py
import json
import tempfile
import traceback
from pathlib import Path
from io import BytesIO

import pandas as pd
import numpy as np
import gradio as gr
import matplotlib.pyplot as plt
from fastapi.responses import PlainTextResponse

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
    ("FX_Schockempfindlichkeit", 0.0, 2.0, default_params.get("FX_Schockempfindlichkeit", 0.8)),
    ("Reserven_Monate", 0, 24, default_params.get("Reserven_Monate", 6)),
]

# -------------------------
# Hilfsfunktionen
# -------------------------
def _load_uploaded_file(uploaded):
    """
    Lädt eine hochgeladene Datei (Gradio UploadedFile) und versucht parquet/csv.
    Gibt DataFrame oder None zurück.
    """
    if uploaded is None:
        return None
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
    """
    Erwartet eine Liste von Slider-Werten in exakt derselben Reihenfolge wie PARAM_SLIDERS.
    Gibt ein dict mit float/int Werten zurück.
    """
    keys = [p[0] for p in PARAM_SLIDERS]
    params = {}
    for k, v in zip(keys, values[: len(keys)]):
        if k == "Reserven_Monate":
            params[k] = int(v)
        else:
            params[k] = float(v)
    return params

def _figure_to_gr_plot(fig):
    """
    Falls plot_summary/plot_years Matplotlib-Figure zurückgeben, geben wir sie direkt zurück.
    Wenn None, erzeugen wir eine leere Figur.
    """
    if fig is None:
        fig = plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "No plot available", ha="center", va="center")
        plt.axis("off")
    return fig

def _save_df_to_temp_csv(df, prefix="samples"):
    """
    Speichert DataFrame in eine temporäre CSV-Datei und gibt den Pfad zurück.
    """
    if df is None or len(df) == 0:
        return None
    tmp = tempfile.NamedTemporaryFile(prefix=prefix + "_", suffix=".csv", delete=False)
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name

# -------------------------
# Callback-Funktionen
# -------------------------
def callback_run_once(*slider_values,
                      N_val=500,
                      seed_val=42,
                      extended_val=True,
                      save_csv_val=False,
                      csv_name_val="samples_run.csv",
                      use_chunk_val=True,
                      chunk_val=200,
                      upload_calib=None):
    """
    Einmalige Simulation (single-run).
    Rückgabe: (summary_text, summary_plot_fig, years_plot_fig, csv_file_path_or_None)
    """
    try:
        params = _collect_params_from_values(slider_values)
        params["N"] = int(N_val)
        params["seed"] = int(seed_val)
        params["use_chunk"] = bool(use_chunk_val)
        params["chunk"] = int(chunk_val) if chunk_val is not None else None

        try:
            params = sanitize_params(params)
        except Exception as e:
            print("sanitize_params Fehler:", e)

        calib_df = _load_uploaded_file(upload_calib)
        if calib_df is not None:
            print("Kalibrierungsdatei geladen, shape:", calib_df.shape)

        if extended_val:
            sim_result = run_simulation_extended(params=params, calib=calib_df)
        else:
            sim_result = run_simulation(params=params, calib=calib_df)

        samples_df = None
        summary_df = None
        if isinstance(sim_result, dict):
            samples_df = sim_result.get("samples") or sim_result.get("df") or sim_result.get("samples_df")
            summary_df = sim_result.get("summary") or sim_result.get("summary_df")
        elif hasattr(sim_result, "shape") and isinstance(sim_result, pd.DataFrame):
            samples_df = sim_result
        else:
            try:
                if isinstance(sim_result, (list, tuple)) and len(sim_result) >= 1:
                    samples_df = sim_result[0]
            except Exception:
                samples_df = None

        try:
            fig_summary = plot_summary(samples_df) if samples_df is not None else None
        except Exception as e:
            print("plot_summary Fehler:", e)
            fig_summary = None

        try:
            fig_years = plot_years(samples_df) if samples_df is not None else None
        except Exception as e:
            print("plot_years Fehler:", e)
            fig_years = None

        fig_summary = _figure_to_gr_plot(fig_summary)
        fig_years = _figure_to_gr_plot(fig_years)

        csv_path = None
        if save_csv_val and samples_df is not None:
            try:
                if csv_name_val:
                    out_path = Path(csv_name_val).name
                    samples_df.to_csv(out_path, index=False)
                    csv_path = str(Path.cwd() / out_path)
                else:
                    csv_path = _save_df_to_temp_csv(samples_df, prefix="samples_once")
            except Exception as e:
                print("CSV speichern Fehler:", e)
                csv_path = _save_df_to_temp_csv(samples_df, prefix="samples_once")

        n_rows = len(samples_df) if samples_df is not None else 0
        summary_text = f"Einmalige Simulation abgeschlossen. Samples: {n_rows} Zeilen."
        if csv_path:
            summary_text += f" CSV gespeichert: {Path(csv_path).name}"

        return summary_text, fig_summary, fig_years, csv_path

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return f"Fehler in run_once: {e}\n{tb}", None, None, None

def callback_run_multi(*slider_values,
                       N_val=100,
                       seed_val=42,
                       years_val=5,
                       extended_val=True,
                       save_csv_val=False,
                       csv_name_val="samples_multi.csv",
                       use_chunk_val=True,
                       chunk_val=200,
                       upload_calib=None):
    """
    Mehrjahres-Simulation: ruft simulate_dynamic_years oder run_simulation_extended mit years auf.
    Rückgabe: (summary_text, summary_plot_fig, years_plot_fig, csv_file_path_or_None)
    """
    try:
        params = _collect_params_from_values(slider_values)
        params["N"] = int(N_val)
        params["seed"] = int(seed_val)
        params["years"] = int(years_val)
        params["use_chunk"] = bool(use_chunk_val)
        params["chunk"] = int(chunk_val) if chunk_val is not None else None

        try:
            params = sanitize_params(params)
        except Exception as e:
            print("sanitize_params Fehler:", e)

        calib_df = _load_uploaded_file(upload_calib)
        if calib_df is not None:
            print("Kalibrierungsdatei geladen, shape:", calib_df.shape)

        sim_result = simulate_dynamic_years(params=params, calib=calib_df)

        samples_df = None
        if isinstance(sim_result, dict):
            samples_df = sim_result.get("samples") or sim_result.get("df") or sim_result.get("samples_df")
        elif hasattr(sim_result, "shape") and isinstance(sim_result, pd.DataFrame):
            samples_df = sim_result
        else:
            try:
                if isinstance(sim_result, (list, tuple)) and len(sim_result) >= 1:
                    samples_df = sim_result[0]
            except Exception:
                samples_df = None

        try:
            fig_summary = plot_summary(samples_df) if samples_df is not None else None
        except Exception as e:
            print("plot_summary Fehler:", e)
            fig_summary = None

        try:
            fig_years = plot_years(samples_df) if samples_df is not None else None
        except Exception as e:
            print("plot_years Fehler:", e)
            fig_years = None

        fig_summary = _figure_to_gr_plot(fig_summary)
        fig_years = _figure_to_gr_plot(fig_years)

        csv_path = None
        if save_csv_val and samples_df is not None:
            try:
                if csv_name_val:
                    out_path = Path(csv_name_val).name
                    samples_df.to_csv(out_path, index=False)
                    csv_path = str(Path.cwd() / out_path)
                else:
                    csv_path = _save_df_to_temp_csv(samples_df, prefix="samples_multi")
            except Exception as e:
                print("CSV speichern Fehler:", e)
                csv_path = _save_df_to_temp_csv(samples_df, prefix="samples_multi")

        n_rows = len(samples_df) if samples_df is not None else 0
        summary_text = f"Mehrjahres-Simulation abgeschlossen. Jahre={params.get('years')}, Gesamtzeilen={n_rows}."
        if csv_path:
            summary_text += f" CSV gespeichert: {Path(csv_path).name}"

        return summary_text, fig_summary, fig_years, csv_path

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return f"Fehler in run_multi: {e}\n{tb}", None, None, None

# -------------------------
# Alternative explizite Callbacks (Teil 2 Integration)
# -------------------------
# Diese Funktionen entsprechen dem UI-Ausschnitt aus Teil 2 und sind
# optional; sie zeigen eine explizite Signatur mit robustem JSON-Parsing.
# Wrapper-Lösung: positional args von Gradio in keyword-only Aufrufe umwandeln
NUM_SLIDERS = len(PARAM_SLIDERS)

def run_once_wrapper(*all_args):
    """
    Erwartet: slider_vals (NUM_SLIDERS) gefolgt von
    [N, seed, extended, save_csv, csv_name, use_chunk, chunk, upload_calib]
    Ruft run_once_explicit mit keyword-Argumenten auf.
    """
    expected = NUM_SLIDERS + 8
    if len(all_args) < expected:
        raise ValueError(f"run_once_wrapper: expected at least {expected} args, got {len(all_args)}")
    slider_vals = all_args[:NUM_SLIDERS]
    rest = all_args[NUM_SLIDERS:]
    N_val, seed_val, extended_val, save_csv_val, csv_name_val, use_chunk_val, chunk_val, upload_file = rest[:8]
    # Debug (optional)
    print("run_once_wrapper received:", "N=", N_val, "seed=", seed_val, "extended=", extended_val)
    return run_once_explicit(
        *slider_vals,
        N_val=N_val,
        seed_val=seed_val,
        extended_val=extended_val,
        save_csv_val=save_csv_val,
        csv_name_val=csv_name_val,
        use_chunk_val=use_chunk_val,
        chunk_val=chunk_val,
        upload_file=upload_file
    )

def run_years_wrapper(*all_args):
    """
    Erwartet: slider_vals (NUM_SLIDERS) gefolgt von
    [N, seed, extended, use_chunk, chunk, years, trends_json, shocks_json, upload_calib]
    Ruft run_years_explicit mit keyword-Argumenten auf.
    """
    expected = NUM_SLIDERS + 9
    if len(all_args) < expected:
        raise ValueError(f"run_years_wrapper: expected at least {expected} args, got {len(all_args)}")
    slider_vals = all_args[:NUM_SLIDERS]
    rest = all_args[NUM_SLIDERS:]
    N_val, seed_val, extended_val, use_chunk_val, chunk_val, years_val, trends_val, shocks_val, upload_file = rest[:9]
    # Debug (optional)
    print("run_years_wrapper received:", "N=", N_val, "years=", years_val, "seed=", seed_val)
    return run_years_explicit(
        *slider_vals,
        N_val=N_val,
        seed_val=seed_val,
        extended_val=extended_val,
        use_chunk_val=use_chunk_val,
        chunk_val=chunk_val,
        years_val=years_val,
        trends_val=trends_val,
        shocks_val=shocks_val,
        upload_file=upload_file
    )

# Ersetze die bisherigen .click(...) Aufrufe durch diese Verkabelung:
# (falls du die .click Aufrufe bereits hattest, entferne/kommentiere die alten und füge diese ein)


def run_once_explicit(
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
            if save_csv_flag and isinstance(csv_or_samples, (str, Path)):
                csv_path = str(csv_or_samples)
            else:
                csv_path = None
        else:
            _, summary = run_simulation(params, N=n, seed=sd, return_samples=False)
            csv_path = None

        fig = plot_summary(summary)
        summary_df = summary.reset_index().rename(columns={"index": "metric"})
        return summary_df, fig, None if csv_path is None else csv_path
    except Exception as e:
        print("run_once_explicit Fehler:", e)
        tb = traceback.format_exc()
        print(tb)
        return pd.DataFrame(), None, None

def run_years_explicit(
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
        print("run_years_explicit Fehler:", e)
        tb = traceback.format_exc()
        print(tb)
        return None, None, pd.DataFrame()

# -------------------------
# Lexikon (Markdown) und UI Aufbau
# -------------------------
def lexikon_erweitert_markdown() -> str:
    return r"""
## 📖 Lexikon: Erweiterte Parameter in der Simulation

### Kernparameter (Standard)
- **USD Dominanz (`USD_Dominanz`)**
  - Anteil der globalen Transaktionen/Reservierungen in US-Dollar.
  - Höhere USD‑Dominanz → stärkere Abhängigkeit; kann Importkosten erhöhen.

- **RMB Akzeptanz (`RMB_Akzeptanz`)**
  - Grad der internationalen Nutzung des Renminbi.
  - Höhere Akzeptanz → alternative Abwicklungswege; kann USD‑Risiko mindern.

- **Zugangsresilienz (`Zugangsresilienz`)**
  - Fähigkeit, Zahlungs- und Handelswege bei Störungen aufrechtzuerhalten.
  - Hohe Resilienz → geringere Volatilität und stabilere Versorgung.

- **Reserven Monate (`Reserven_Monate`)**
  - Anzahl Monate, die durch Devisenreserven finanziert werden können.
  - Mehr Monate → höhere Pufferkapazität.

- **FX Schockempfindlichkeit (`FX_Schockempfindlichkeit`)**
  - Empfindlichkeit gegenüber Wechselkursschocks (UI erlaubt 0.0–2.0).
  - Höhere Werte → größere Schwankungen in Preisen und Kosten.

- **Sanktions Exposure (`Sanktions_Exposure`)**
  - Anteil der Wirtschaftsbeziehungen, die durch Sanktionen gefährdet sind.
  - Höheres Exposure → erhöhtes Risiko für Handelsunterbrechungen.

- **Alternativnetz Abdeckung (`Alternativnetz_Abdeckung`)**
  - Verfügbarkeit alternativer Zahlungs‑/Abwicklungsnetzwerke.
  - Größere Abdeckung → bessere Ausweichmöglichkeiten bei Störungen.

- **Liquiditaetsaufschlag (`Liquiditaetsaufschlag`)**
  - Zusatzkosten bei knapper Liquidität.
  - Höherer Aufschlag → steigende Importkosten.

- **CBDC Nutzung (`CBDC_Nutzung`)**
  - Verbreitung digitaler Zentralbankwährungen.
  - Höhere Nutzung → potenziell effizientere Abwicklung, Einfluss auf Resilienz.

- **Golddeckung (`Golddeckung`)**
  - Anteil der Reserven in Gold.
  - Höhere Golddeckung → stabilisierender Puffer in Krisen.

### Erweiterte Parameter (Erweitert‑Simulation)
- **Innovationskraft (`innovation`)**
  - Technologische und wirtschaftliche Innovationsfähigkeit.
  - Schwache Innovation → höhere Importkosten; starke Innovation → senkt Importkosten.

- **Fachkräfteangebot (`fachkraefte`)**
  - Verfügbarkeit qualifizierter Arbeitskräfte.
  - Mehr Fachkräfte → höhere Resilienz.

- **Politische Stabilität (`stabilitaet`)**
  - Institutionelle und politische Verlässlichkeit.
  - Hohe Stabilität → stärkt Resilienz.

- **Energiepreise / Wettbewerbsfähigkeit (`energie`)**
  - Einfluss der Energiepreise auf Kostenstruktur.
  - Hohe Energiepreise → mehr Volatilität.

- **Staatsverschuldung (`verschuldung`)**
  - Verhältnis der Schulden zum BIP (UI 0–2 möglich).
  - Höhere Verschuldung → tendenziell höhere Volatilität; intern optional auf 0–1 skaliert.

### Neuer Parameter: Demokratie (`demokratie`)
- **Definition**
  - Skala **0.0 – 1.0**; 0 = autoritär/geringe Rechenschaftspflicht, 1 = stabile, inklusive Demokratie mit funktionierenden Institutionen.
- **Direkte Effekte im Modell**
  - **Resilienz**: Demokratie erhöht `netto_resilienz` (z. B. additiv), weil Rechtsstaat, Transparenz und Rechenschaft Investitions‑ und Anpassungsfähigkeit fördern.
  - **Volatilität**: Demokratie reduziert `system_volatilitaet` (z. B. kleinerer Basiseffekt), da Informationsflüsse und Institutionen Schocks dämpfen.
  - **Importkosten**: Demokratie kann `importkosten_mult` leicht senken durch besseren Eigentumsschutz und geringere Transaktionskosten.

... (voller Text in der Originaldatei kann hier stehen) ...
"""

def build_demo():
    with gr.Blocks() as demo:
        gr.Markdown("## Makro‑Simulator — interaktive Oberfläche")

        # Layout: drei Spalten (Parameter | Aktionen/Ergebnisse | Lexikon)
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Parameter")
                sliders = {}
                for name, lo, hi, val in PARAM_SLIDERS:
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

            with gr.Column(scale=2):
                gr.Markdown("### Aktionen")
                btn_run = gr.Button("Einmalige Simulation ausführen")
                btn_years = gr.Button("Mehrjahres‑Simulation ausführen")

                gr.Markdown("### Ergebnisse")
                summary_table = gr.Dataframe(headers=["metric","p05","median","p95"], label="Summary (Quantile)", row_count=10)
                summary_plot = gr.Plot(label="Summary Plot")
                years_table = gr.Dataframe(headers=["Jahr","Importkosten","Resilienz","Volatilität"], label="Mehrjahres‑Tabelle", row_count=20)
                years_plot = gr.Plot(label="Mehrjahres‑Plot")
                csv_output = gr.File(label="CSV Ergebnis (Download)")

            # Rechts: Lexikon (erscheint nur wenn Platz vorhanden); initial sichtbar
            with gr.Column(scale=1):
                gr.Markdown("### Lexikon")
                lexikon_md = gr.Markdown(lexikon_erweitert_markdown(), elem_id="lexikon-panel", visible=True)
                lexikon_state = gr.State(value=True)
                toggle_btn = gr.Button("Lexikon ein-/ausblenden")

                # Toggle callback: nimmt aktuellen State, gibt Update und neuen State zurück
                def _toggle_lexikon(state: bool):
                    new_state = not bool(state)
                    return gr.update(visible=new_state), new_state

                toggle_btn.click(fn=_toggle_lexikon, inputs=[lexikon_state], outputs=[lexikon_md, lexikon_state])

        # Inputs list: slider components in order + controls
        slider_components = [sliders[name] for name, _, _, _ in PARAM_SLIDERS]
        inputs_run = slider_components + [N, seed, extended_flag, save_csv, csv_name, use_chunk, chunk, upload_calib]
        inputs_years = slider_components + [N, seed, extended_flag, use_chunk, chunk, years, trends_json, shocks_json, upload_calib]

        # Verkabelung: Einmalige Simulation (explizite Variante)
        btn_run.click(
            fn=run_once_wrapper,
            inputs=inputs_run,
            outputs=[summary_table, summary_plot, csv_output]
        )

        # Verkabelung: Mehrjahres-Simulation (explizite Variante)
        btn_years.click(
            fn=run_years_wrapper,
            inputs=inputs_years,
            outputs=[summary_table, years_plot, years_table]
        )

    return demo

demo = build_demo()

# --- HTTP Endpunkt /lexikon registrieren (liefert reines Markdown) ---
try:
    app = demo.app  # FastAPI app, verfügbar bei Gradio >= 3.x
    @app.get("/lexikon")
    def _get_lexikon():
        return PlainTextResponse(lexikon_erweitert_markdown(), media_type="text/markdown")
except Exception:
    # Falls demo.app nicht verfügbar ist (sehr alte Gradio-Version), ignorieren wir still.
    pass
