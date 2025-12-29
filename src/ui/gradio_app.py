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
# Default-Parameter & Slider-Definitionen
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Slider-Preset-Datei sicherstellen
# ---------------------------------------------------------------------

def _ensure_presets_file():
    PRESETS_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    if not PRESETS_FILENAME.exists():
        PRESETS_FILENAME.write_text("{}", encoding="utf-8")


# ---------------------------------------------------------------------
# Slider-Preset-IO
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


def get_preset(name: str):
    p = load_presets()
    return p.get(name)


# ---------------------------------------------------------------------
# Risiko-Scores
# ---------------------------------------------------------------------

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_risk_scores(p: dict) -> Dict[str, float]:
    macro = (
        clamp01(p.get("verschuldung", 0.8) / 2.0) * 0.4 +
        clamp01(p.get("FX_Schockempfindlichkeit", 0.8) / 2.0) * 0.3 +
        (1 - clamp01(p.get("Reserven_Monate", 6) / 24.0)) * 0.3
    )

    geo = (
        clamp01(p.get("USD_Dominanz", 0.7)) * 0.4 +
        clamp01(p.get("Sanktions_Exposure", 0.05)) * 0.4 +
        (1 - clamp01(p.get("Alternativnetz_Abdeckung", 0.5))) * 0.2
    )

    gov = (
        (1 - clamp01(p.get("demokratie", 0.8))) * 0.5 +
        (1 - clamp01(p.get("innovation", 0.6))) * 0.3 +
        (1 - clamp01(p.get("fachkraefte", 0.7))) * 0.2
    )

    total = 0.5 * macro + 0.3 * geo + 0.2 * gov

    return {
        "macro": clamp01(macro),
        "geo": clamp01(geo),
        "governance": clamp01(gov),
        "total": clamp01(total),
    }


def risk_category(score: float) -> Tuple[str, str]:
    if score < 0.34:
        return "stabil", "green"
    elif score < 0.67:
        return "warnung", "yellow"
    else:
        return "kritisch", "red"


def get_scored_preset_choices():
    presets = load_presets()
    choices = []
    for name, preset in presets.items():
        try:
            scores = compute_risk_scores(preset)
            cat, _color = risk_category(scores["total"])
            if cat == "stabil":
                label = f"🟢 {name}"
            elif cat == "warnung":
                label = f"🟡 {name}"
            else:
                label = f"🔴 {name}"
        except Exception:
            label = name
        choices.append((label, name))
    return choices


# ---------------------------------------------------------------------
# Validierung der Slider-Presets
# ---------------------------------------------------------------------

def validate_slider_preset(preset: dict) -> List[str]:
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

    for key in preset.keys():
        if key not in expected_keys:
            errors.append(f"Unknown key in preset: {key}")

    return errors


def validate_all_slider_presets() -> Dict[str, List[str]]:
    presets = load_presets()
    result: Dict[str, List[str]] = {}
    for name, preset in presets.items():
        errs = validate_slider_preset(preset)
        if errs:
            result[name] = errs
    return result


def _log_preset_validation():
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
# Konvertierungs-Pipeline (UI-Variante)
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


def generate_slider_presets_from_countries() -> str:
    """
    UI-Variante: nutzt das Mapping aus scripts/generate_slider_presets.py.
    """
    try:
        from scripts.generate_slider_presets import country_to_slider_preset
    except Exception as e:
        print("Konnte country_to_slider_preset nicht importieren:", e)
        return "Fehler: Mapping-Funktion konnte nicht importiert werden."

    countries = _load_country_presets()
    if not countries:
        return "Keine country_presets.json gefunden oder Datei leer."

    slider_presets = load_presets()
    generated = 0
    for code, country_preset in countries.items():
        try:
            sp = country_to_slider_preset(code, country_preset)
            slider_presets[code] = sp
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
    params = {}
    for (key, lo, hi, default), val in zip(PARAM_SLIDERS, slider_vals):
        params[key] = float(val)
    return params


def _save_preset_and_refresh_dropdown(*all_vals):
    import traceback
    try:
        num = NUM_SLIDERS
        slider_vals = all_vals[:num]
        name = all_vals[num] if len(all_vals) > num else None

        if not name or not isinstance(name, str) or not name.strip():
            return "Kein Preset-Name angegeben.", gr.update(choices=get_scored_preset_choices())

        name = name.strip()
        params = _collect_params_from_values(list(slider_vals))

        try:
            from .sanitize import sanitize_params
            params = sanitize_params(params)
        except Exception:
            pass

        presets = load_presets()
        presets[name] = params
        ok = save_presets(presets)

        if ok:
            return (
                f"Preset '{name}' gespeichert.",
                gr.update(choices=get_scored_preset_choices(), value=name),
            )
        else:
            return (
                f"Fehler beim Speichern von '{name}'.",
                gr.update(choices=get_scored_preset_choices()),
            )
    except Exception as e:
        print("Exception in save:", e)
        print(traceback.format_exc())
        return f"Fehler: {e}", gr.update(choices=get_scored_preset_choices())


def _delete_preset_and_refresh_dropdown(name: str):
    presets = load_presets()
    if name in presets:
        del presets[name]
        ok = save_presets(presets)
    else:
        ok = False
    return (
        "Gelöscht." if ok else "Nicht gefunden.",
        gr.update(choices=get_scored_preset_choices(), value=None),
    )


def _load_preset_with_warning(preset_name: str, *current_vals):
    try:
        if not preset_name:
            none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]
            return (*none_updates, "Kein Preset ausgewählt.")

        presets = load_presets()
        preset = presets.get(preset_name)
        if not preset:
            none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]
            return (*none_updates, f"Preset '{preset_name}' nicht gefunden.")

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
# Lexikon (Markdown) und UI Aufbau
# ---------------------------------------------------------------------

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

### A)Makro‑Risiko
- **Verschuldung**
- **Inflation**
- **FX‑Schockempfindlichkeit**
- **Reserven**

### B) Geopolitisches Risiko
- **USD‑Dominanz**
- **Sanktions‑Exposure**
- **Alternativnetz‑Abdeckung (invertiert)**

### C) Governance‑Risiko
- **Demokratie (invertiert)**
- **Innovation (invertiert)**
- **Fachkräfte (invertiert)**

### Gesamt‑Risiko: 0.5 * risk_macro(p) + 0.3 * risk_geo(p) + 0.2 * risk_governance(p)

### Farbliche Markierung (kritisch / warnend / stabil)
| **Score** | **Kategorie** | **Farbe** |
|---|---|---|
| **0.00–0.33** | **Stabil** | Grün |
| **0.34–0.66** | **Warnung** | Gelb |
| **0.67–1.00** | **Kritisch** | Rot |

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
# UI bauen
# ---------------------------------------------------------------------

_log_preset_validation()

with gr.Blocks(title="Makro-Simulation") as demo:
    gr.Markdown("# Makro-Simulation")

    # -------------------------------------------------------------
    # Simulation (inkl. Risiko-Output)
    # -------------------------------------------------------------
    with gr.Tab("Simulation"):
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
        summary_text = gr.Textbox(label="Ergebnis-Summary", lines=12)

        def dummy_run(*vals):
            params = _collect_params_from_values(list(vals))
            scores = compute_risk_scores(params)
            cat, _color = risk_category(scores["total"])

            out = {
                "params": params,
                "risk_scores": scores,
                "risk_category": cat,
            }
            return json.dumps(out, indent=2, ensure_ascii=False)

        btn_run.click(
            fn=dummy_run,
            inputs=slider_components,
            outputs=summary_text,
        )

    # -------------------------------------------------------------
    # Preset-Manager
    # -------------------------------------------------------------
    with gr.Tab("Preset-Manager"):
        gr.Markdown("### Preset Manager")

        preset_dropdown = gr.Dropdown(
            choices=get_scored_preset_choices(),
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

        btn_load_preset.click(
            fn=_load_preset_with_warning,
            inputs=[preset_dropdown] + slider_components,
            outputs=[*slider_components, preset_status],
        )

        btn_save_preset.click(
            fn=_save_preset_and_refresh_dropdown,
            inputs=slider_components + [preset_name],
            outputs=[preset_status, preset_dropdown],
        )

        btn_delete_preset.click(
            fn=_delete_preset_and_refresh_dropdown,
            inputs=[preset_dropdown],
            outputs=[preset_status, preset_dropdown],
        )

    # -------------------------------------------------------------
    # Preset-Diagnose
    # -------------------------------------------------------------
    with gr.Tab("Preset-Diagnose"):
        gr.Markdown("### Diagnose der Slider-Presets")

        btn_validate = gr.Button("Slider-Presets prüfen")
        diag_output = gr.Markdown()

        def run_validation():
            errors_by_preset = validate_all_slider_presets()
            presets = load_presets()

            lines = []
            lines.append("#### Risiko-Übersicht")
            lines.append("| Preset | Macro | Geo | Governance | Total | Kategorie |")
            lines.append("|---|---:|---:|---:|---:|---|")
            for name, preset in presets.items():
                scores = compute_risk_scores(preset)
                cat, _ = risk_category(scores["total"])
                lines.append(
                    f"| {name} | "
                    f"{scores['macro']:.2f} | {scores['geo']:.2f} | {scores['governance']:.2f} | "
                    f"{scores['total']:.2f} | {cat} |"
                )

            if not errors_by_preset:
                lines.append("\n✅ Alle Slider-Presets sind strukturell gültig.")
            else:
                lines.append("\n⚠️ Strukturelle Probleme bei folgenden Presets:")
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

        def run_conversion():
            msg = generate_slider_presets_from_countries()
            return msg, gr.update(choices=get_scored_preset_choices())

        btn_convert.click(
            fn=run_conversion,
            inputs=None,
            outputs=[convert_status, preset_dropdown],
        )

    # -------------------------------------------------------------
    # Lexikon
    # -------------------------------------------------------------
    with gr.Tab("Lexikon"):
        gr.Markdown(lexikon_erweitert_markdown())


if __name__ == "__main__":
    demo.launch()
