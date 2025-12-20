# src/ui/gradio_app.py
import json
import tempfile
import traceback
from pathlib import Path
from io import BytesIO
from datetime import datetime

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

# --- Preset-Manager Hilfsfunktionen ---
PRESETS_FILENAME = DATA_DIR / "presets.json" if DATA_DIR is not None else Path("presets.json")

def _ensure_presets_file():
    try:
        PRESETS_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    if not PRESETS_FILENAME.exists():
        # initial example presets (illustrative, not real-world accurate)
        example = {
            "Exportorientiertes_Land": {
                "USD_Dominanz": 0.6, "RMB_Akzeptanz": 0.1, "Zugangsresilienz": 0.85,
                "Sanktions_Exposure": 0.02, "Alternativnetz_Abdeckung": 0.6, "Liquiditaetsaufschlag": 0.02,
                "CBDC_Nutzung": 0.3, "Golddeckung": 0.2, "innovation": 0.7, "fachkraefte": 0.8,
                "energie": 0.5, "stabilitaet": 0.9, "verschuldung": 0.6, "demokratie": 0.8,
                "FX_Schockempfindlichkeit": 0.7, "Reserven_Monate": 6
            },
            "Importabhängiges_Land": {
                "USD_Dominanz": 0.8, "RMB_Akzeptanz": 0.05, "Zugangsresilienz": 0.6,
                "Sanktions_Exposure": 0.1, "Alternativnetz_Abdeckung": 0.3, "Liquiditaetsaufschlag": 0.05,
                "CBDC_Nutzung": 0.1, "Golddeckung": 0.1, "innovation": 0.4, "fachkraefte": 0.5,
                "energie": 0.7, "stabilitaet": 0.6, "verschuldung": 1.0, "demokratie": 0.5,
                "FX_Schockempfindlichkeit": 1.2, "Reserven_Monate": 3
            },
            "Hohe_Resilienz": {
                "USD_Dominanz": 0.5, "RMB_Akzeptanz": 0.2, "Zugangsresilienz": 0.95,
                "Sanktions_Exposure": 0.01, "Alternativnetz_Abdeckung": 0.9, "Liquiditaetsaufschlag": 0.01,
                "CBDC_Nutzung": 0.6, "Golddeckung": 0.4, "innovation": 0.9, "fachkraefte": 0.9,
                "energie": 0.4, "stabilitaet": 0.95, "verschuldung": 0.4, "demokratie": 0.9,
                "FX_Schockempfindlichkeit": 0.5, "Reserven_Monate": 12
            }
        }
        try:
            PRESETS_FILENAME.write_text(json.dumps(example, indent=2), encoding="utf-8")
        except Exception:
            pass

def load_presets():
    _ensure_presets_file()
    try:
        text = PRESETS_FILENAME.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception:
        return {}

def save_presets(presets: dict):
    _ensure_presets_file()
    try:
        PRESETS_FILENAME.write_text(json.dumps(presets, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False

def get_preset_names():
    p = load_presets()
    return sorted(list(p.keys()))

def get_preset(name: str):
    p = load_presets()
    return p.get(name)

def save_preset(name: str, params: dict):
    if not name or not isinstance(name, str):
        return False
    p = load_presets()
    p[name] = params
    return save_presets(p)

def delete_preset(name: str):
    p = load_presets()
    if name in p:
        del p[name]
        return save_presets(p)
    return False


def _preview_import_file(uploaded):
    """
    Robust: akzeptiert Gradio UploadedFile oder Pfad-String.
    Returns: (preview_rows, parsed_json_or_error_str)
    preview_rows: list of [preset_name, status, sample_keys]
    parsed_json_or_error_str: dict (parsed JSON) oder Fehler-String
    """
    try:
        if not uploaded:
            return [], "Keine Datei ausgewählt."

        # 1) Wenn Gradio UploadedFile-Objekt (has .file or .name)
        content_text = None
        # uploaded may be a tuple/list (older gradio) -> take first
        if isinstance(uploaded, (list, tuple)):
            uploaded = uploaded[0]

        # If it's a path-like string
        if isinstance(uploaded, str):
            p = Path(uploaded)
            if not p.exists():
                return [], f"Dateipfad nicht gefunden: {uploaded}"
            content_text = p.read_text(encoding="utf-8")

        else:
            # Try common attributes
            #  - uploaded.name may be filename only
            #  - uploaded.file is a file-like object
            #  - uploaded.read() may exist
            if hasattr(uploaded, "file") and hasattr(uploaded.file, "read"):
                uploaded.file.seek(0)
                raw = uploaded.file.read()
                if isinstance(raw, bytes):
                    content_text = raw.decode("utf-8")
                else:
                    content_text = str(raw)
            elif hasattr(uploaded, "read"):
                raw = uploaded.read()
                if isinstance(raw, bytes):
                    content_text = raw.decode("utf-8")
                else:
                    content_text = str(raw)
            else:
                # fallback: try name as path
                path = getattr(uploaded, "name", None)
                if path and Path(path).exists():
                    content_text = Path(path).read_text(encoding="utf-8")
                else:
                    return [], "Konnte Dateiinhalt nicht lesen (unbekannter Upload‑Typ)."

        # Trim and quick empty check
        if content_text is None or not content_text.strip():
            return [], "Datei ist leer oder enthält nur Whitespaces."

        # Parse JSON
        try:
            data = json.loads(content_text)
        except Exception as e:
            return [], f"Fehler beim Parsen der JSON: {e}"

        if not isinstance(data, dict):
            return [], "Ungültiges Format: JSON muss ein Objekt (dict) mit Preset-Namen sein."

        existing = load_presets()
        rows = []
        for name, params in data.items():
            status = "neu" if name not in existing else "konflikt"
            sample_keys = ",".join(list(params.keys())[:3]) if isinstance(params, dict) else ""
            rows.append([name, status, sample_keys])
        return rows, data

    except Exception as e:
        import traceback
        print("Preview import Fehler:", e)
        print(traceback.format_exc())
        return [], f"Unerwarteter Fehler: {e}"

def _atomic_save_presets(presets: dict) -> bool:
    try:
        PRESETS_FILENAME.parent.mkdir(parents=True, exist_ok=True)
        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(delete=False, dir=PRESETS_FILENAME.parent, suffix=".tmp")
        tmp.write(json.dumps(presets, indent=2, ensure_ascii=False).encode("utf-8"))
        tmp.close()
        Path(tmp.name).replace(PRESETS_FILENAME)
        return True
    except Exception as e:
        print("atomic save error:", e)
        return False


def _confirm_import(parsed_json, strategy: str):
    """
    parsed_json: dict (aus _preview_import_file)
    strategy: "überschreiben" | "überspringen" | "umbenennen"
    """
    try:
        if not isinstance(parsed_json, dict):
            return "Keine gültigen Presets zum Importieren.", gr.update(choices=get_preset_names())
        presets = load_presets()
        added = []
        skipped = []
        renamed = []
        for name, params in parsed_json.items():
            if name in presets:
                if strategy == "überspringen":
                    skipped.append(name)
                    continue
                if strategy == "überschreiben":
                    presets[name] = params
                    added.append(name)
                    continue
                if strategy == "umbenennen":
                    base = name
                    i = 1
                    candidate = f"{base}_{i}"
                    while candidate in presets:
                        i += 1
                        candidate = f"{base}_{i}"
                    presets[candidate] = params
                    renamed.append((name, candidate))
                    continue
            else:
                presets[name] = params
                added.append(name)
        # atomisch speichern
        ok = _atomic_save_presets(presets)
        if not ok:
            return "Fehler beim Schreiben der Presets.", gr.update(choices=get_preset_names())
        msg = f"Import fertig. Hinzugefügt: {len(added)}; Übersprungen: {len(skipped)}; Umbenannt: {len(renamed)}"
        return msg, gr.update(choices=get_preset_names(), value=None)
    except Exception as e:
        return f"Import-Fehler: {e}", gr.update(choices=get_preset_names())


def _export_preset_with_meta(preset_name: str, author: str):
    p = get_preset(preset_name)
    if not p:
        return None
    export_obj = {
        "metadata": {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "author": author or "unknown",
            "source_file": str(PRESETS_FILENAME.resolve())
        },
        "presets": { preset_name: p }
    }
    # temporäre Datei erzeugen
    tmp = tempfile.NamedTemporaryFile(prefix=f"preset_export_{preset_name}_", suffix=".json", delete=False)
    tmp.write(json.dumps(export_obj, indent=2, ensure_ascii=False).encode("utf-8"))
    tmp.close()
    return tmp.name   # Gradio akzeptiert Pfad als File-Output

def _import_preset_file(uploaded):
    """
    Importiert eine JSON-Datei mit Presets. Robust gegenüber:
    - gr.File UploadedFile (has .file / .name)
    - Pfad-String
    - list/tuple mit erstem Element
    Rückgabe: (ok: bool, dropdown_update)
    """
    try:
        if not uploaded:
            return False, gr.update(choices=get_preset_names())

        if isinstance(uploaded, (list, tuple)):
            uploaded = uploaded[0]

        # read content
        content = None
        if hasattr(uploaded, "file") and hasattr(uploaded.file, "read"):
            uploaded.file.seek(0)
            raw = uploaded.file.read()
            content = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        elif isinstance(uploaded, str) and Path(uploaded).exists():
            content = Path(uploaded).read_text(encoding="utf-8")
        elif hasattr(uploaded, "name") and Path(getattr(uploaded, "name")).exists():
            content = Path(getattr(uploaded, "name")).read_text(encoding="utf-8")
        elif hasattr(uploaded, "read"):
            raw = uploaded.read()
            content = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        else:
            return False, gr.update(choices=get_preset_names())

        if not content or not content.strip():
            return False, gr.update(choices=get_preset_names())

        data = json.loads(content)
        if not isinstance(data, dict):
            return False, gr.update(choices=get_preset_names())

        presets = load_presets()
        presets.update(data)
        ok = save_presets(presets)
        return bool(ok), gr.update(choices=get_preset_names())
    except Exception as e:
        import traceback
        print("Import Preset Fehler:", e)
        print(traceback.format_exc())
        return False, gr.update(choices=get_preset_names())

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

                # Preset-Manager UI
                gr.Markdown("### Preset Manager")
                preset_dropdown = gr.Dropdown(choices=get_preset_names(), label="Preset wählen", value=None)
                btn_load_preset = gr.Button("Preset laden")
                preset_name = gr.Textbox(label="Neuer Preset-Name", value="", placeholder="Name für aktuelles Set")
                btn_save_preset = gr.Button("Als Preset speichern")
                btn_delete_preset = gr.Button("Preset löschen")

                # Import UI
                btn_import_file = gr.File(label="Preset JSON auswählen", file_types=[".json"], file_count="single")
                import_preview = gr.Dataframe(headers=["preset_name","status","sample_keys"], label="Import Vorschau", row_count=10)
                import_status = gr.Textbox(label="Import Status", visible=True)
                conflict_strategy = gr.Radio(choices=["überschreiben","überspringen","umbenennen"], value="überschreiben")
                btn_confirm_import = gr.Button("Import bestätigen")
                parsed_json_store = gr.State()  # Hidden state to carry parsed JSON between callbacks

                # Export
                export_author = gr.Textbox(label="Autor (für Export‑Metadaten)", value="")
                btn_export_preset = gr.Button("Export (JSON mit Metadaten)")
                btn_import_preset = gr.File(label="Importiere Preset JSON", file_count="single")

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
                export_file = gr.File(label="Exportdatei")

                save_status = gr.Textbox(label="Save status", value="", visible=True)
                del_status = gr.Textbox(label="Delete status", value="", visible=True)
                import_status_hidden = gr.Textbox(label="import_ok", value="", visible=False)

            with gr.Column(scale=1):
                gr.Markdown("### Lexikon")
                lexikon_md = gr.Markdown(lexikon_erweitert_markdown(), elem_id="lexikon-panel", visible=True)
                lexikon_state = gr.State(value=True)
                toggle_btn = gr.Button("Lexikon ein-/ausblenden")

                def _toggle_lexikon(state: bool):
                    new_state = not bool(state)
                    return gr.update(visible=new_state), new_state

                toggle_btn.click(fn=_toggle_lexikon, inputs=[lexikon_state], outputs=[lexikon_md, lexikon_state])

        # Prepare input lists for run functions
        slider_components = [sliders[name] for name, _, _, _ in PARAM_SLIDERS]
        inputs_run = slider_components + [N, seed, extended_flag, save_csv, csv_name, use_chunk, chunk, upload_calib]
        inputs_years = slider_components + [N, seed, extended_flag, use_chunk, chunk, years, trends_json, shocks_json, upload_calib]

        # --- Callback Hilfsfunktionen ---

        def _apply_preset_to_sliders(preset_name):
            preset = get_preset(preset_name)
            if not preset:
                return [gr.update(value=None) for _ in slider_components]
            updates = []
            for name, _, _, _ in PARAM_SLIDERS:
                val = preset.get(name)
                updates.append(gr.update(value=val))
            return updates

        def _save_current_as_preset(*all_vals):
            import traceback
            try:
                num = NUM_SLIDERS if 'NUM_SLIDERS' in globals() else len(PARAM_SLIDERS)
                name = None
                if len(all_vals) >= num + 1:
                    name = all_vals[num]
                    slider_vals = all_vals[:num]
                else:
                    slider_vals = all_vals[:num]
                if not name or not isinstance(name, str) or not name.strip():
                    return "Kein Preset-Name angegeben.", gr.update(choices=get_preset_names())
                name = name.strip()
                params = _collect_params_from_values(slider_vals)
                try:
                    params = sanitize_params(params)
                except Exception:
                    pass
                ok = save_preset(name, params)
                if ok:
                    return f"Preset '{name}' gespeichert.", gr.update(choices=get_preset_names(), value=name)
                else:
                    return f"Fehler beim Speichern von '{name}'.", gr.update(choices=get_preset_names())
            except Exception as e:
                print("Exception in save:", e)
                print(traceback.format_exc())
                return f"Fehler: {e}", gr.update(choices=get_preset_names())

        def _delete_preset(name):
            ok = delete_preset(name)
            return ("Gelöscht." if ok else "Nicht gefunden."), gr.update(choices=get_preset_names(), value=None)

        def _export_preset(name):
            p = get_preset(name)
            if not p:
                return None
            tmp = tempfile.NamedTemporaryFile(prefix="preset_", suffix=".json", delete=False)
            tmp.write(json.dumps({name: p}, indent=2, ensure_ascii=False).encode("utf-8"))
            tmp.close()
            return tmp.name

        # Robust preview import function (gibt immer 3 Werte zurück)
        def _preview_import_file(uploaded):
            try:
                if not uploaded:
                    return [], None, "Keine Datei ausgewählt."
                if isinstance(uploaded, (list, tuple)):
                    uploaded = uploaded[0]
                content_text = None
                if hasattr(uploaded, "file") and hasattr(uploaded.file, "read"):
                    uploaded.file.seek(0)
                    raw = uploaded.file.read()
                    content_text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
                elif isinstance(uploaded, str) and Path(uploaded).exists():
                    content_text = Path(uploaded).read_text(encoding="utf-8")
                elif hasattr(uploaded, "name") and Path(getattr(uploaded, "name")).exists():
                    content_text = Path(getattr(uploaded, "name")).read_text(encoding="utf-8")
                elif hasattr(uploaded, "read"):
                    raw = uploaded.read()
                    content_text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
                else:
                    return [], None, "Konnte Dateiinhalt nicht lesen (unbekannter Upload‑Typ)."
                if not content_text or not content_text.strip():
                    return [], None, "Datei ist leer oder enthält nur Whitespaces."
                try:
                    data = json.loads(content_text)
                except Exception as e:
                    return [], None, f"Fehler beim Parsen der JSON: {e}"
                if not isinstance(data, dict):
                    return [], None, "Ungültiges Format: JSON muss ein Objekt (dict) mit Preset-Namen sein."
                existing = load_presets()
                rows = []
                for name, params in data.items():
                    status = "neu" if name not in existing else "konflikt"
                    sample_keys = ",".join(list(params.keys())[:3]) if isinstance(params, dict) else ""
                    rows.append([name, status, sample_keys])
                return rows, data, "Vorschau geladen. Prüfe die Einträge und bestätige den Import."
            except Exception as e:
                import traceback
                print("Preview import Fehler:", e)
                print(traceback.format_exc())
                return [], None, f"Unerwarteter Fehler: {e}"

        # Confirm import wrapper (nutzt _confirm_import)
        def _on_confirm_import(parsed_json, strategy):
            if not parsed_json:
                return "Keine Vorschau vorhanden. Bitte zuerst Datei auswählen und Vorschau laden.", gr.update(choices=get_preset_names())
            msg, dropdown_update = _confirm_import(parsed_json, strategy)
            return msg, dropdown_update

        # Export with metadata wrapper
        def _on_export_preset(name, author):
            path = _export_preset_with_meta(name, author)
            if path:
                return path, "Export bereit."
            return None, "Export fehlgeschlagen."

        # --- Verkabelung / Bindings ---

        # Simulation Buttons
        btn_run.click(fn=run_once_wrapper, inputs=inputs_run, outputs=[summary_table, summary_plot, csv_output])
        btn_years.click(fn=run_years_wrapper, inputs=inputs_years, outputs=[summary_table, years_plot, years_table])

        # Preset Buttons
        btn_load_preset.click(fn=_apply_preset_to_sliders, inputs=[preset_dropdown], outputs=slider_components)
        btn_save_preset.click(fn=_save_current_as_preset, inputs=slider_components + [preset_name], outputs=[save_status, preset_dropdown])
        btn_delete_preset.click(fn=_delete_preset, inputs=[preset_dropdown], outputs=[del_status, preset_dropdown])
        btn_export_preset.click(fn=_on_export_preset, inputs=[preset_dropdown, export_author], outputs=[export_file, import_status])

        # File import (preview) -> gibt (rows, parsed_json, status)
        # parsed_json_store ist gr.State und erhält das geparste dict
        btn_import_file.upload(fn=_preview_import_file, inputs=[btn_import_file], outputs=[import_preview, parsed_json_store, import_status])
        # Bestätigen des Imports: parsed_json_store + strategy -> status + dropdown update
        btn_confirm_import.click(fn=_on_confirm_import, inputs=[parsed_json_store, conflict_strategy], outputs=[import_status, preset_dropdown])

        # Direktes Preset-Import (alternative, falls Nutzer eine Preset-Datei direkt importieren will)
        btn_import_preset.upload(fn=_import_preset_file, inputs=[btn_import_preset], outputs=[import_status, preset_dropdown])

    return demo

# Erzeuge und starte das Demo (oder exportiere demo)
demo = build_demo()

try:
    app = demo.app
    @app.get("/lexikon")
    def _get_lexikon():
        return PlainTextResponse(lexikon_erweitert_markdown(), media_type="text/markdown")
except Exception as e:
    print("Kein demo.app verfügbar, /lexikon nicht registriert:", e)
