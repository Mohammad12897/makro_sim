#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Tuple

import gradio as gr

# ---------------------------------------------------------------------
# Pfade & Basis-Setup
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRESETS_DIR = BASE_DIR / "presets"

# UI-Presets (flach, für Slider)
PRESETS_FILENAME = PRESETS_DIR / "slider_presets.json"

# Länder-Presets (Indicator-Snapshots, Metadaten)
COUNTRY_PRESETS_FILENAME = PRESETS_DIR / "country_presets.json"


# ---------------------------------------------------------------------
# Default-Parameter & Slider-Definitionen (hier deine existierenden defaults)
# ---------------------------------------------------------------------

# Beispiel: default_params wird irgendwo zuvor aus einem Default-Dict gefüllt
default_params: Dict[str, float] = {
    "USD_Dominanz": 0.7,
    "RMB_Akzeptanz": 0.2,
    "Zugangsresilienz": 0.8,
    "Sanktions_Exposure": 0.05,
    "Alternativnetz_Abdeckung": 0.5,
    "Liquiditaetsaufschlag": 0.03,
    "CBDC_Nutzung": 0.5,
    "Golddeckung": 0.4,
    "innovation": 0.6,
    "fachkraefte": 0.7,
    "energie": 0.5,
    "stabilitaet": 0.9,
    "verschuldung": 0.8,
    "demokratie": 0.8,
    "FX_Schockempfindlichkeit": 0.8,
    "Reserven_Monate": 6,
}

# Deine echte PARAM_SLIDERS-Definition:
PARAM_SLIDERS: List[Tuple[str, float, float, float]] = [
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

NUM_SLIDERS = len(PARAM_SLIDERS)


def normalize_ratio(value, min_val=0.0, max_val=3.0):
    if value is None:
        return 0.5
    x = value
    x = max(min_val, min(max_val, x))
    return (x - min_val) / (max_val - min_val)

# -------------------------
# Lexikon (Markdown) und UI Aufbau
# -------------------------
def lexikon_erweitert_markdown() -> str:
    return r"""

### Kritische Werte und Hinweise

| **Parameter** | **Risiko Schwelle** | **Warum kritisch** | **Empfohlene Aktion** |
|---|---:|---|---|
| **USD_Dominanz** | **> 0.75** | Starke Abhängigkeit vom US‑Dollar erhöht Import‑ und Finanzrisiko | Diversifikation prüfen; RMB_Akzeptanz erhöhen |
| **RMB_Akzeptanz** | **< 0.05** | Sehr geringe Akzeptanz reduziert Ausweichmöglichkeiten | Zahlungsrails und Handelsabkommen fördern |
| **Zugangsresilienz** | **< 0.5** | Niedrige Resilienz → hohe Unterbrechungsanfälligkeit | Infrastruktur und Alternativnetz ausbauen |
| **Reserven_Monate** | **< 3** Monate | Geringe Puffer für Importfinanzierung | Reserven aufstocken; Kreditlinien sichern |
| **FX_Schockempfindlichkeit** | **> 1.2** | Hohe Empfindlichkeit → starke Preisvolatilität | Hedging, Liquiditätsmanagement verstärken |
| **Sanktions_Exposure** | **> 0.1** | Hohes Exposure → reale Handelsrisiken | Lieferketten diversifizieren; Compliance prüfen |
| **Alternativnetz_Abdeckung** | **< 0.3** | Wenig Ausweichnetz → eingeschränkte Optionen bei Störungen | Alternative Zahlungswege aufbauen |
| **Liquiditaetsaufschlag** | **> 0.05** | Hohe Zusatzkosten bei Knappheit | Liquiditätsreserven erhöhen |
| **CBDC_Nutzung** | **< 0.1 oder > 0.9** | Sehr niedrig: verpasste Effizienz; sehr hoch: neue Abhängigkeiten | Technologie und Governance prüfen |
| **Golddeckung** | **< 0.05** | Sehr geringe Golddeckung reduziert Krisenpuffer | Diversifikation der Reserven erwägen |
| **verschuldung** | **> 1.0 (UI Skala)** | Sehr hohe Verschuldung erhöht fiskalische Verwundbarkeit | Konsolidierung, externe Finanzierung prüfen |
| **demokratie** | **< 0.3** | Geringe Rechenschaft → erhöhtes politisches Risiko | Governance Maßnahmen und Transparenz stärken |

#### Validierungsregeln beim Import
- **Typprüfung**: `Reserven_Monate` muss **int** sein; andere numerische Parameter **float**.
- **Bereichsprüfung**: Werte außerhalb der UI‑Grenzen werden **geclamped** (auf nächstzulässigen Wert) oder als Fehler markiert.
- **Sanity Checks**: Kombinationen wie `Reserven_Monate < 3` und `USD_Dominanz > 0.7` erzeugen eine **Kritisch**‑Warnung.
- **UI Verhalten**: In der Import‑Vorschau werden Presets mit `Warnung` oder `Kritisch` markiert; beim Bestätigen wird eine Zusammenfassung angezeigt.

### Neuer Parameter: Demokratie (`demokratie`)
- **Definition**
  - Skala **0.0 – 1.0**; 0 = autoritär/geringe Rechenschaftspflicht, 1 = stabile, inklusive Demokratie mit funktionierenden Institutionen.
- **Direkte Effekte im Modell**
  - **Resilienz**: Demokratie erhöht `netto_resilienz` (z. B. additiv), weil Rechtsstaat, Transparenz und Rechenschaft Investitions‑ und Anpassungsfähigkeit fördern.
  - **Volatilität**: Demokratie reduziert `system_volatilitaet` (z. B. kleinerer Basiseffekt), da Informationsflüsse und Institutionen Schocks dämpfen.
  - **Importkosten**: Demokratie kann `importkosten_mult` leicht senken durch besseren Eigentumsschutz und geringere Transaktionskosten.


"""

# ---------------------------------------------------------------------
# Slider-Preset-Datei sicherstellen
# ---------------------------------------------------------------------

def _ensure_presets_file():
    PRESETS_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    if not PRESETS_FILENAME.exists():
        # Leere Struktur, keine Beispiel-Presets mehr
        PRESETS_FILENAME.write_text("{}", encoding="utf-8")


# ---------------------------------------------------------------------
# Slider-Preset-IO (für slider_presets.json)
# ---------------------------------------------------------------------

def load_presets() -> dict:
    _ensure_presets_file()
    try:
        text = PRESETS_FILENAME.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            print("Warning: slider_presets.json ist nicht vom Typ dict, setze auf {}.")
            return {}
        return data
    except Exception as e:
        print("Error reading slider_presets.json:", e)
        return {}


def save_presets(presets: dict) -> bool:
    _ensure_presets_file()
    try:
        PRESETS_FILENAME.write_text(
            json.dumps(presets, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        print("Error writing slider_presets.json:", e)
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


# ---------------------------------------------------------------------
# Validierung der Slider-Presets
# ---------------------------------------------------------------------

def validate_slider_preset(preset: dict) -> List[str]:
    """
    Validiert ein flaches Slider-Preset gegen PARAM_SLIDERS.
    Gibt eine Liste von Fehlermeldungen zurück (leer = gültig).
    """
    errors: List[str] = []

    if not isinstance(preset, dict):
        return ["Preset ist kein Dict."]

    expected_keys = {k for (k, _lo, _hi, _default) in PARAM_SLIDERS}

    for key, lo, hi, default in PARAM_SLIDERS:
        if key not in preset:
            errors.append(f"Missing key: {key}")
            continue
        val = preset[key]
        if not isinstance(val, (int, float)):
            errors.append(f"Invalid type for {key}: {type(val).__name__}, expected number")
            continue
        if not (lo <= val <= hi):
            errors.append(f"Value out of range: {key}={val} not in [{lo}, {hi}]")

    # Unbekannte Keys melden (optional)
    for key in preset.keys():
        if key not in expected_keys:
            errors.append(f"Unknown key in preset: {key}")

    return errors


def validate_all_slider_presets() -> Dict[str, List[str]]:
    """
    Validiert alle Slider-Presets in slider_presets.json.
    Rückgabe: {preset_name: [errors...], ...}
    """
    presets = load_presets()
    result: Dict[str, List[str]] = {}
    for name, preset in presets.items():
        errs = validate_slider_preset(preset)
        if errs:
            result[name] = errs
    return result


def _log_preset_validation():
    """
    Validiert beim Start alle Slider-Presets und schreibt eine hübsche,
    gut lesbare Ausgabe ins Terminal.
    """
    print("=== Validierung der Slider-Presets (slider_presets.json) ===")
    errors_by_preset = validate_all_slider_presets()
    if not errors_by_preset:
        print("Alle Slider-Presets sind gültig.\n")
        return

    for name, errs in errors_by_preset.items():
        print(f"- {name}:")
        for e in errs:
            print(f"    * {e}")
    print("=== Ende der Präset-Validierung ===\n")


# ---------------------------------------------------------------------
# Konvertierungs-Pipeline (country_presets.json → slider_presets.json)
# ---------------------------------------------------------------------

def _load_country_presets() -> dict:
    if not COUNTRY_PRESETS_FILENAME.exists():
        return {}
    try:
        text = COUNTRY_PRESETS_FILENAME.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            print("Warning: country_presets.json ist nicht vom Typ dict.")
            return {}
        return data
    except Exception as e:
        print("Error reading country_presets.json:", e)
        return {}


def country_to_slider_preset(country_code: str, country_preset: dict) -> dict:
    """
    Dummy-Konvertierung: hier kannst du deine echte Logik einbauen.
    Aktuell: Basis auf defaults + ein Beispiel-Mapping für 'verschuldung'.
    """
    slider_preset = {k: default for (k, _lo, _hi, default) in PARAM_SLIDERS}
    snapshot = country_preset.get("indicator_snapshot", {}) or {}

    # Beispiel-Mapping: Verschuldung basierend auf DT_DOD_DECT_CD / NY_GDP_MKTP_CD
    try:
        debt = snapshot.get("DT_DOD_DECT_CD", {}).get("value")
        gdp = snapshot.get("NY_GDP_MKTP_CD", {}).get("value")
        if debt is not None and gdp:
            ratio = debt / gdp
            # einfache Normalisierung: 0..1 bei 0..3
            val = max(0.0, min(1.0, ratio / 3.0))
            slider_preset["verschuldung"] = val
    except Exception:
        pass

    # Hier kannst du weitere Mappings für energie, stabilitaet, etc. ergänzen.

    return slider_preset


def generate_slider_presets_from_countries() -> str:
    """
    Liest country_presets.json, erzeugt für jedes Land ein Slider-Preset
    und schreibt sie in slider_presets.json. Gibt Status-Text zurück.
    """
    countries = _load_country_presets()
    if not countries:
        return "Keine country_presets.json gefunden oder Datei leer."

    slider_presets = load_presets()  # vorhandene Slider-Presets bleiben erhalten

    generated = 0
    for code, country_preset in countries.items():
        try:
            slider_presets[code] = country_to_slider_preset(code, country_preset)
            generated += 1
        except Exception as e:
            print(f"Error generating slider preset for {code}: {e}")

    ok = save_presets(slider_presets)
    if ok:
        return f"{generated} Slider-Presets aus Länder-Presets erzeugt."
    else:
        return "Fehler beim Schreiben von slider_presets.json."


# ---------------------------------------------------------------------
# UI-Hilfsfunktionen (Preset-Manager)
# ---------------------------------------------------------------------

def _collect_params_from_values(slider_vals: List[float]) -> dict:
    """
    Baut aus einer Liste von Slider-Werten ein Dict {key: value}.
    """
    params = {}
    for (key, lo, hi, default), val in zip(PARAM_SLIDERS, slider_vals):
        params[key] = float(val)
    return params


def _save_current_as_preset(*all_vals):
    import traceback
    try:
        num = NUM_SLIDERS
        slider_vals = all_vals[:num]
        name = all_vals[num] if len(all_vals) > num else None

        if not name or not isinstance(name, str) or not name.strip():
            return "Kein Preset-Name angegeben.", gr.update(choices=get_preset_names())

        name = name.strip()
        params = _collect_params_from_values(list(slider_vals))

        # Optional: sanitize_params(params) einbauen, falls vorhanden
        try:
            from .sanitize import sanitize_params  # falls du so etwas hast
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


def _delete_preset(name: str):
    ok = delete_preset(name)
    return ("Gelöscht." if ok else "Nicht gefunden."), gr.update(choices=get_preset_names(), value=None)


def _load_preset_with_warning(preset_name: str, *current_vals):
    """
    Lädt ein Preset, validiert es (nur prüfen, nicht clampen) und gibt:
    (slider_update_1, ..., slider_update_N, status_text) zurück.
    """
    try:
        if not preset_name:
            none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]
            return (*none_updates, "Kein Preset ausgewählt.")

        preset = get_preset(preset_name)
        if not preset:
            none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]
            return (*none_updates, f"Preset '{preset_name}' nicht gefunden.")

        # Hier optional deine vorhandene validate_preset-Funktion nutzen:
        try:
            from .sanitize import validate_preset
            clean, warnings = validate_preset(preset, clamp=False)
        except Exception:
            clean = preset
            warnings = []

        updates = []
        for key, lo, hi, default in PARAM_SLIDERS:
            val = clean.get(key, default)
            updates.append(gr.update(value=val))

        if any(w[0] == "critical" for w in warnings):
            status = "Achtung: Preset enthält kritische Werte."
        elif warnings:
            status = "Warnungen im Preset vorhanden."
        else:
            status = "Preset geladen."

        return (*updates, status)
    except Exception as e:
        import traceback
        print("Fehler in _load_preset_with_warning:", e)
        print(traceback.format_exc())
        none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]
        return (*none_updates, f"Fehler beim Laden des Presets: {e}")


# ---------------------------------------------------------------------
# UI bauen
# ---------------------------------------------------------------------

_log_preset_validation()  # einmal beim Start prüfen und ins Terminal loggen


with gr.Blocks(title="Makro-Simulation") as demo:
    gr.Markdown("# Makro-Simulation")

    with gr.Tab("Simulation"):
        # -----------------------------------------------------------------
        # HIER: deine bestehende Simulation-UI einbauen:
        # - Slider aus PARAM_SLIDERS
        # - Buttons: Run, Run Years, etc.
        # - Outputs: Tabellen, Plots, CSV
        # Ich mache nur ein minimalistisches Beispiel.
        # -----------------------------------------------------------------
        slider_components = []
        for key, lo, hi, default in PARAM_SLIDERS:
            slider = gr.Slider(
                minimum=lo,
                maximum=hi,
                value=default,
                step=0.01,
                label=key,
            )
            slider_components.append(slider)

        btn_run = gr.Button("Simulation starten")
        summary_text = gr.Textbox(label="Ergebnis-Summary")

        def dummy_run(*vals):
            params = _collect_params_from_values(list(vals))
            return json.dumps(params, indent=2, ensure_ascii=False)

        btn_run.click(
            fn=dummy_run,
            inputs=slider_components,
            outputs=summary_text,
        )

    with gr.Tab("Preset-Manager"):
        gr.Markdown("### Preset Manager")

        preset_dropdown = gr.Dropdown(
            choices=get_preset_names(),
            label="Preset wählen",
            value=None,
        )
        btn_load_preset = gr.Button("Preset laden")

        preset_name = gr.Textbox(
            label="Neuer Preset-Name",
            value="",
            placeholder="Name für aktuelles Set",
        )
        btn_save_preset = gr.Button("Als Preset speichern")
        btn_delete_preset = gr.Button("Preset löschen")

        preset_status = gr.Markdown("")

        # Laden: Slider updaten + Status
        btn_load_preset.click(
            fn=_load_preset_with_warning,
            inputs=[preset_dropdown] + slider_components,
            outputs=[*slider_components, preset_status],
        )

        # Speichern: Status + Dropdown aktualisieren
        btn_save_preset.click(
            fn=_save_current_as_preset,
            inputs=slider_components + [preset_name],
            outputs=[preset_status, preset_dropdown],
        )

        # Löschen: Status + Dropdown aktualisieren
        btn_delete_preset.click(
            fn=_delete_preset,
            inputs=[preset_dropdown],
            outputs=[preset_status, preset_dropdown],
        )

    with gr.Tab("Preset-Diagnose"):
        gr.Markdown("### Diagnose der Slider-Presets")

        btn_validate = gr.Button("Slider-Presets prüfen")
        diag_output = gr.Markdown()
        
        def run_validation():
            errors_by_preset = validate_all_slider_presets()
            if not errors_by_preset:
                return "✅ Alle Slider-Presets sind gültig."
            lines = ["⚠️ Probleme bei folgenden Presets:"]
            for name, errs in errors_by_preset.items():
                lines.append(f"- **{name}**")
                for e in errs:
                    lines.append(f"    - {e}")
            return "\n".join(lines)

        btn_validate.click(
            fn=run_validation,
            inputs=None,
            outputs=diag_output,
        )

        gr.Markdown("---")
        gr.Markdown("### Länder → Slider-Presets")

        btn_convert = gr.Button("Slider-Presets aus Länder-Presets erzeugen")
        convert_status = gr.Markdown()

    with gr.Tab("Lexikon"):
        gr.Markdown(lexikon_erweitert_markdown())

        def run_conversion():
            msg = generate_slider_presets_from_countries()
            # Dropdown aktualisieren, damit neue Länder-Presets sichtbar werden
            return msg, gr.update(choices=get_preset_names())

        btn_convert.click(
            fn=run_conversion,
            inputs=None,
            outputs=[convert_status, preset_dropdown],
        )


if __name__ == "__main__":
    demo.launch()
