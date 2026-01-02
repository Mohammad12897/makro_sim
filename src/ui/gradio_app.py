#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.risk_model import compute_risk_scores, risk_category

import json
import math
import random
from pathlib import Path
from typing import List, Dict, Tuple

import gradio as gr
import matplotlib.pyplot as plt
import numpy as np



def build_comment_a(summary):
    g = summary["final_gdp_growth_det"]
    inf = summary["final_inflation_det"]
    risk = summary["final_risk_det"]

    parts = []
    parts.append("Wachstum: robust." if g > 0.03 else "Wachstum: moderat." if g > 0 else "Wachstum: rezessiv.")
    parts.append("Inflation: hoch." if inf > 0.06 else "erhöht." if inf > 0.03 else "unter Kontrolle.")
    parts.append("Risiko: kritisch." if risk > 0.66 else "angespannt." if risk > 0.33 else "stabil.")
    return " ".join(parts)


def build_comment_b(summary):
    return (
        f"Importkosten: {summary['final_importkosten_mult_det']:.2f}. "
        f"Alternativnetz: {summary['alternativnetz_abdeckung']:.2f}. "
        f"Währungsdiversifikation: {summary['waehrungsdiversifikation']:.2f}."
    )


def build_comment_c(summary):
    return (
        f"Systemvolatilität: {summary['system_vol_det']:.2f}. "
        f"Schock-Propagation: {summary['schock_propagation_proxy']:.2f}. "
        f"Governance-Stabilität: {summary['governance_stability_proxy']:.2f}. "
        f"Stressindex: {summary['final_stress_det']:.2f}."
    )


def build_comment_d(summary):
    return (
        f"MC-Wachstum: {summary['gdp_growth_mean_final']:.2f}. "
        f"MC-Inflation: {summary['inflation_mean_final']:.2f}. "
        f"MC-Risiko: {summary['risk_drift_mean_final']:.2f}."
    )


# ---------------------------------------------------------------------
# Pfade & Basis-Setup
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PRESETS_DIR = BASE_DIR / "presets"

PRESETS_FILENAME = PRESETS_DIR / "slider_presets.json"
COUNTRY_PRESETS_FILENAME = PRESETS_DIR / "country_presets.json"

# ---------------------------------------------------------------------
# Slider-Definitionen
# ---------------------------------------------------------------------

SCENARIOS = ["Baseline", "Optimistisch", "Pessimistisch", "Stress"]

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
    "korruption": 0.3,
}

PARAM_SLIDERS: List[Tuple[str, float, float, float]] = [
    ("USD_Dominanz", 0.0, 1.0, default_params["USD_Dominanz"]),
    ("RMB_Akzeptanz", 0.0, 1.0, default_params["RMB_Akzeptanz"]),
    ("Zugangsresilienz", 0.0, 1.0, default_params["Zugangsresilienz"]),
    ("Sanktions_Exposure", 0.0, 1.0, default_params["Sanktions_Exposure"]),
    ("Alternativnetz_Abdeckung", 0.0, 1.0, default_params["Alternativnetz_Abdeckung"]),
    ("Liquiditaetsaufschlag", 0.0, 1.0, default_params["Liquiditaetsaufschlag"]),
    ("CBDC_Nutzung", 0.0, 1.0, default_params["CBDC_Nutzung"]),
    ("Golddeckung", 0.0, 1.0, default_params["Golddeckung"]),
    ("innovation", 0.0, 1.0, default_params["innovation"]),
    ("fachkraefte", 0.0, 1.0, default_params["fachkraefte"]),
    ("energie", 0.0, 1.0, default_params["energie"]),
    ("stabilitaet", 0.0, 1.0, default_params["stabilitaet"]),
    ("verschuldung", 0.0, 2.0, default_params["verschuldung"]),
    ("demokratie", 0.0, 1.0, default_params["demokratie"]),
    ("FX_Schockempfindlichkeit", 0.0, 2.0, default_params["FX_Schockempfindlichkeit"]),
    ("Reserven_Monate", 0, 24, default_params["Reserven_Monate"]),
    ("korruption", 0.0, 1.0, default_params["korruption"]),
]

NUM_SLIDERS = len(PARAM_SLIDERS)

# ---------------------------------------------------------------------
# Preset-IO + Auto-Pipeline
# ---------------------------------------------------------------------

def _ensure_presets_file():
    PRESETS_FILENAME.parent.mkdir(parents=True, exist_ok=True)
    if not PRESETS_FILENAME.exists():
        PRESETS_FILENAME.write_text("{}", encoding="utf-8")


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


def ensure_slider_presets_up_to_date() -> str:
    """
    Auto-Pipeline:
    - Falls slider_presets.json fehlt, generieren
    - Falls country_presets.json neuer ist, neu generieren
    """
    from scripts.generate_slider_presets import main as gen_main

    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    if not COUNTRY_PRESETS_FILENAME.exists():
        return "country_presets.json fehlt – Auto-Generierung von Slider-Presets übersprungen."

    if not PRESETS_FILENAME.exists():
        print("slider_presets.json fehlt – generiere neu.")
        gen_main()
        return "slider_presets.json neu erzeugt."

    country_mtime = COUNTRY_PRESETS_FILENAME.stat().st_mtime
    slider_mtime = PRESETS_FILENAME.stat().st_mtime

    if country_mtime > slider_mtime:
        print("country_presets.json ist neuer – generiere slider_presets.json neu.")
        gen_main()
        return "slider_presets.json aktualisiert (neu aus country_presets.json erzeugt)."

    return "slider_presets.json ist aktuell."

# ---------------------------------------------------------------------
# Risiko-Scores
# ---------------------------------------------------------------------

def collapse_alarm(det):
    warnings = []

    if det["gdp_growth"][-1] < -0.03:
        warnings.append("🔴 BIP kollabiert (< -3%)")

    if det["inflation"][-1] > 0.08:
        warnings.append("🔴 Hyperinflation (> 8%)")

    if det["resilienz"][-1] < 0.2:
        warnings.append("🔴 Resilienz kritisch (< 0.2)")

    if det["risk_drift"][-1] > 0.8:
        warnings.append("🔴 Systemrisiko extrem (> 0.8)")

    if det["stress_index"][-1] > 0.7:
        warnings.append("🔴 Stressindex kritisch (> 0.7)")

    if not warnings:
        return "🟢 Keine Kollaps‑Warnungen"

    return "\n".join(warnings)


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

def build_risk_radar(preset: dict, title: str = "Risiko-Radar"):
    scores = compute_risk_scores(preset)
    labels = ["Macro", "Geo", "Governance"]
    values = [scores["macro"], scores["geo"], scores["governance"]]

    # Radar schließt sich am Ende: ersten Wert anhängen
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels) + 1)

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(5, 5))
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(angles[:-1] * 180 / np.pi, labels)
    ax.set_ylim(0, 1)
    ax.set_title(title, fontsize=14, pad=20)
    ax.text(
        0.5, 1.10,
        "Δ = Live – Baseline (5D Risiko-Komponenten)",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
    )
    fig.tight_layout()
    plt.close(fig)
    return fig


def build_risk_radar_5d(scores: dict, title: str):
    import matplotlib.pyplot as plt
    import numpy as np

    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]
    values = [
        scores["macro"],
        scores["geo"],
        scores["governance"],
        scores["finanz"],
        scores["sozial"],
    ]

    # Radar schließen
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(values))

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))

    # Hintergrund
    ax.set_facecolor("#f7f7f7")

    # Gitterlinien
    ax.set_rlabel_position(0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8"], fontsize=9)
    ax.set_ylim(0, 1)

    # Linien + Fläche
    ax.plot(angles, values, linewidth=2, color="#0077cc")
    ax.fill(angles, values, color="#0077cc", alpha=0.25)

    # Achsenbeschriftung
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)

    # Titel
    ax.set_title(title, fontsize=14, pad=20)

    # Formel-Erklärung oben drüber
    ax.text(
        0.5, 1.08,
        "Total = 0.5·Makro + 0.3·Geo + 0.2·Governance",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
    )

    fig.tight_layout()
    plt.close(fig)
    return fig

def build_early_warning(params: dict) -> dict:
    scores = compute_risk_scores(params)
    warnings = []

    if scores["macro"] > 0.7:
        warnings.append("Makro-Risiko hoch: Verschuldung/Reserven kritisch.")
    if scores["geo"] > 0.7:
        warnings.append("Geopolitisches Risiko hoch: Abhängigkeit & Sanktions-Exposure.")
    if scores["governance"] > 0.7:
        warnings.append("Governance-Risiko hoch: institutionelle Schwäche.")

    cat, _ = risk_category(scores["total"])
    if cat == "kritisch":
        level = "🔴 Kritisch"
    elif cat == "warnung":
        level = "🟡 Warnung"
    else:
        level = "🟢 Stabil"

    return {
        "level": level,
        "scores": scores,
        "messages": warnings,
    }

# ---------------------------------------------------------------------
# Validierung & Diagnose
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


def build_risk_tables_and_figures():
    presets = load_presets()
    names = sorted(presets.keys())
    if not names:
        return "Keine Slider-Presets gefunden.", None, None

    rows = []
    macro_vals, geo_vals, gov_vals, total_vals = [], [], [], []
    for name in names:
        scores = compute_risk_scores(presets[name])
        cat, _ = risk_category(scores["total"])
        rows.append((name, scores, cat))
        macro_vals.append(scores["macro"])
        geo_vals.append(scores["geo"])
        gov_vals.append(scores["governance"])
        total_vals.append(scores["total"])

    lines = []
    lines.append("#### Risiko-Übersicht")
    lines.append("| Preset | Macro | Geo | Governance | Total | Kategorie |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for name, scores, cat in rows:
        lines.append(
            f"| {name} | "
            f"{scores['macro']:.2f} | {scores['geo']:.2f} | {scores['governance']:.2f} | "
            f"{scores['total']:.2f} | {cat} |"
        )
    table_md = "\n".join(lines)

    data = np.array([
        [compute_risk_scores(presets[name])["macro"],
         compute_risk_scores(presets[name])["geo"],
         compute_risk_scores(presets[name])["governance"]]
        for name in names
    ])
    fig_heat, ax = plt.subplots(figsize=(6, max(3, 0.4 * len(names))))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(names)))
    ax.set_yticklabels(names)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(["Macro", "Geo", "Governance"])
    plt.colorbar(im, ax=ax, label="Risiko (0–1)")
    plt.tight_layout()

    fig_bar, ax2 = plt.subplots(figsize=(6, max(3, 0.4 * len(names))))
    y_pos = np.arange(len(names))
    ax2.barh(y_pos, total_vals, color="orange")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names)
    ax2.set_xlabel("Total-Risiko")
    ax2.set_xlim(0, 1)
    plt.tight_layout()

    return table_md, fig_heat, fig_bar


# ---------------------------------------------------------------------
# Lexikon
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

### A) Makro‑Risiko
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
| **netto_resilienz=** | **Zugangsresilienz * (1 - risk_macro)** |
| **importkosten_mult=** | **1 + risk_geo * 0.2** |
| **system_volatilitaet=** | **0.1 + risk_governance * 0.3** |

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
# Preset-Manager Hilfsfunktionen
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

            # NEUE OUTPUTS HINZUFÜGEN
            return (
                *none_updates,
                "Kein Preset ausgewählt.",
                gr.update(value=None),   # live_risk_box
                gr.update(value=None),   # live_radar_plot
                gr.update(value=None),   # delta_radar_plot
                gr.update(value=None),   # risk_thermo
            )

        presets = load_presets()
        preset = presets.get(preset_name)
        if not preset:
            none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]

            return (
                *none_updates,
                f"Preset '{preset_name}' nicht gefunden.",
                gr.update(value=None),
                gr.update(value=None),
                gr.update(value=None),
                gr.update(value=None),
            )

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

        # HIER KOMMEN DIE 4 NEUEN OUTPUTS DAZU
        return (
            *updates,
            status,
            gr.update(value=None),   # live_risk_box
            gr.update(value=None),   # live_radar_plot
            gr.update(value=None),   # delta_radar_plot
            gr.update(value=None),   # risk_thermo
        )

    except Exception as e:
        import traceback
        print("Fehler in _load_preset_with_warning:", e)
        print(traceback.format_exc())

        none_updates = [gr.update(value=None) for _ in PARAM_SLIDERS]

        return (
            *none_updates,
            f"Fehler beim Laden des Presets: {e}",
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
        )

def normalize_inflation(value: float, mean: float = 4.0, std: float = 3.0) -> float:
    if value is None:
        return 0.5
    z = (value - mean) / std
    risk = 1.0 / (1.0 + math.exp(-z))  # Sigmoid
    return clamp01(risk)

def normalize_inflation_zscore(value, mean=4.0, std=3.0):
    if value is None:
        return 0.5
    z = (float(value) - mean) / std
    # Sigmoid, damit extrem hohe Werte nicht alles dominieren
    risk = 1 / (1 + math.exp(-z))
    return clamp01(risk)

# ---------------------------------------------------------------------
# Basissimulation mit Risiko
# ---------------------------------------------------------------------

def simulate_with_risk(*vals):
    params = _collect_params_from_values(list(vals))
    scores = compute_risk_scores(params)
    cat, _color = risk_category(scores["total"])

    netto_resilienz = params["Zugangsresilienz"] * (1 - scores["macro"]) * (1 - 0.5 * scores["geo"])
    importkosten_mult = 1.0 + 0.4 * scores["geo"] + 0.2 * scores["macro"]
    system_volatilitaet = 0.1 + 0.6 * scores["governance"] + 0.3 * scores["macro"]
    schock_durchleitung = scores["geo"] * 0.7 + scores["macro"] * 0.3

    overall_stress = (
        0.4 * scores["macro"] +
        0.3 * scores["geo"] +
        0.3 * scores["governance"]
    )

    out = {
        "params": params,
        "risk_scores": scores,
        "risk_category": cat,
        "simulation": {
            "netto_resilienz": netto_resilienz,
            "importkosten_mult": importkosten_mult,
            "system_volatilitaet": system_volatilitaet,
            "schock_durchleitung": schock_durchleitung,
            "overall_stress": overall_stress,
        },
    }
    return json.dumps(out, indent=2, ensure_ascii=False)

def apply_scenario(params: dict, scenario: str) -> dict:
    p = params.copy()
    if scenario == "Optimistisch":
        p["demokratie"] = min(1.0, p.get("demokratie", 0.8) + 0.1)
        p["innovation"] = min(1.0, p.get("innovation", 0.6) + 0.1)
        p["Zugangsresilienz"] = min(1.0, p.get("Zugangsresilienz", 0.8) + 0.1)
        p["Sanktions_Exposure"] = max(0.0, p.get("Sanktions_Exposure", 0.05) - 0.02)
    elif scenario == "Pessimistisch":
        p["demokratie"] = max(0.0, p.get("demokratie", 0.8) - 0.2)
        p["innovation"] = max(0.0, p.get("innovation", 0.6) - 0.1)
        p["Zugangsresilienz"] = max(0.0, p.get("Zugangsresilienz", 0.8) - 0.2)
        p["Sanktions_Exposure"] = min(1.0, p.get("Sanktions_Exposure", 0.05) + 0.05)
    elif scenario == "Stress":
        p["FX_Schockempfindlichkeit"] = min(2.0, p.get("FX_Schockempfindlichkeit", 0.8) + 0.5)
        p["Reserven_Monate"] = max(0.0, p.get("Reserven_Monate", 6) - 3)
        p["verschuldung"] = min(2.0, p.get("verschuldung", 0.8) + 0.3)
    # Baseline = unverändert
    return p

# ---------------------------------------------------------------------
# Prognose-Engine (deterministisch, stochastisch, Monte-Carlo)
# ---------------------------------------------------------------------

def simulate_paths(params: dict, years: int, runs: int, events: dict | None = None):
    events = events or {}

    # Risiko-Basiswerte
    scores = compute_risk_scores(params)
    macro = scores["macro"]
    geo = scores["geo"]
    gov = scores["governance"]
    total = scores["total"]

    # Baseline-Parameter
    base_growth = 0.03
    base_inflation = 0.02
    base_resilienz = params.get("Zugangsresilienz", 0.8)

    # Abgeleitete Größen
    system_vol = 0.1 + 0.6 * gov + 0.3 * macro
    schock_durchl = geo * 0.7 + macro * 0.3
    import_mult_base = 1.0 + 0.4 * geo + 0.2 * macro
    stress_base = 0.4 * macro + 0.3 * geo + 0.3 * gov

    # ---------------------------------------------------------
    # DETERMINISTISCH
    # ---------------------------------------------------------
    det = {k: [] for k in [
        "gdp_growth", "inflation", "resilienz", "risk_drift",
        "importkosten_mult", "system_vol", "stress_index"
    ]}

    resil = base_resilienz
    risk_level = total
    import_mult = import_mult_base
    stress = stress_base

    for t in range(years):
        event = events.get(t, {})

        shock_add = event.get("shock_add", 0.0)
        geo_add = event.get("geo_risk_add", 0.0)
        macro_add = event.get("macro_risk_add", 0.0)
        resil_add = event.get("resilienz_add", 0.0)

        geo_eff = min(1.0, geo + geo_add)
        macro_eff = min(1.0, macro + macro_add)

        shock_effect = shock_add

        growth = base_growth * (1 - 0.8 * risk_level) - 0.02 * shock_effect
        infl = base_inflation + 0.5 * system_vol + shock_effect

        resil = max(0.0, min(1.0,
            resil * (1 - 0.4 * schock_durchl) +
            0.1 * (1 - stress) +
            resil_add -
            0.1 * shock_effect
        ))

        import_mult = import_mult * (1 + 0.1 * (geo_eff - resil))
        stress = max(0.0, min(1.0, stress + 0.1 * (macro_eff - gov) + 0.05 * shock_effect))
        risk_level = max(0.0, min(1.0, risk_level + 0.05 * (macro_eff - gov) + 0.02 * shock_effect))

        det["gdp_growth"].append(growth)
        det["inflation"].append(infl)
        det["resilienz"].append(resil)
        det["risk_drift"].append(risk_level)
        det["importkosten_mult"].append(import_mult)
        det["system_vol"].append(system_vol)
        det["stress_index"].append(stress)

    # ---------------------------------------------------------
    # STOCHASTISCH
    # ---------------------------------------------------------
    stoch = {k: [] for k in [
        "gdp_growth", "inflation", "resilienz", "risk_drift",
        "importkosten_mult", "system_vol", "stress_index"
    ]}

    resil_s = base_resilienz
    risk_level_s = total
    import_mult_s = import_mult_base
    stress_s = stress_base

    for t in range(years):
        shock = random.gauss(0, system_vol)

        growth_s = base_growth * (1 - total) + 0.02 * shock
        infl_s = base_inflation + shock

        resil_s = max(0.0, min(1.0,
            resil_s * (1 - 0.4 * schock_durchl) +
            0.15 * (1 - stress_s) -
            0.1 * abs(shock)
        ))

        import_mult_s = import_mult_s * (1 + 0.1 * (geo - resil_s) + 0.05 * shock)
        stress_s = max(0.0, min(1.0, stress_s + 0.1 * (macro - gov) + 0.05 * abs(shock)))
        risk_level_s = max(0.0, min(1.0, risk_level_s + 0.05 * (macro - gov) + 0.02 * shock))

        stoch["gdp_growth"].append(growth_s)
        stoch["inflation"].append(infl_s)
        stoch["resilienz"].append(resil_s)
        stoch["risk_drift"].append(risk_level_s)
        stoch["importkosten_mult"].append(import_mult_s)
        stoch["system_vol"].append(system_vol)
        stoch["stress_index"].append(stress_s)

    # ---------------------------------------------------------
    # MONTE-CARLO
    # ---------------------------------------------------------
    mc = {k: [] for k in ["gdp_growth", "inflation", "resilienz", "risk_drift"]}

    for _ in range(runs):
        resil_m = base_resilienz
        risk_level_m = total
        stress_m = stress_base

        g_list, i_list, r_list, rd_list = [], [], [], []

        for t in range(years):
            shock = random.gauss(0, system_vol)

            g = base_growth * (1 - total) + 0.02 * shock
            inf = base_inflation + shock

            resil_m = max(0.0, min(1.0,
                resil_m * (1 - 0.4 * schock_durchl) +
                0.15 * (1 - stress_m) -
                0.1 * abs(shock)
            ))

            risk_level_m = max(0.0, min(1.0, risk_level_m + 0.05 * (macro - gov) + 0.02 * shock))

            g_list.append(g)
            i_list.append(inf)
            r_list.append(resil_m)
            rd_list.append(risk_level_m)

        mc["gdp_growth"].append(g_list)
        mc["inflation"].append(i_list)
        mc["resilienz"].append(r_list)
        mc["risk_drift"].append(rd_list)

    return det, stoch, mc

def build_fan_plot(mc_series, years: int, title: str):
    arr = np.array(mc_series)
    t = np.arange(years)

    mean = np.mean(arr, axis=0)
    p5 = np.percentile(arr, 5, axis=0)
    p95 = np.percentile(arr, 95, axis=0)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(t, mean, color="blue", label="Mittelwert")
    ax.fill_between(t, p5, p95, color="blue", alpha=0.2, label="5–95% Band")
    ax.set_title(title)
    ax.set_xlabel("Jahre")
    ax.legend()
    plt.tight_layout()
    plt.close(fig)
    return fig


# ---------------------------------------------------------------------
# Start: Auto-Pipeline + Validierung loggen
# ---------------------------------------------------------------------

status_auto = ensure_slider_presets_up_to_date()
print("Auto-Pipeline:", status_auto)
_log_preset_validation()

# ---------------------------------------------------------------------
# UI bauen
# ---------------------------------------------------------------------

def risk_thermometer(total_risk: float) -> str:
    if total_risk < 0.33:
        return "🟢 **Stabil** – geringes Gesamtrisiko"
    elif total_risk < 0.66:
        return "🟡 **Angespannt** – mittleres Gesamtrisiko"
    else:
        return "🔴 **Kritisch** – hohes Gesamtrisiko"

def update_live_risk_and_radar(*vals):
    params = _collect_params_from_values(list(vals))
    scores_live = compute_risk_scores(params)

    # Baseline = Startwerte der Slider
    params_base = _collect_params_from_values([s.value for s in slider_components])
    scores_base = compute_risk_scores(params_base)

    radar_live = build_risk_radar_5d(scores_live, "Live-Risiko-Radar")
    radar_delta = build_delta_radar(scores_base, scores_live)

    thermometer = risk_thermometer(scores_live["total"])

    return scores_live, radar_live, radar_delta, thermometer


def build_delta_radar(scores_base, scores_live, title="Delta-Radar"):
    import matplotlib.pyplot as plt
    import numpy as np

    labels = ["Makro", "Geo", "Governance", "Finanz", "Sozial"]

    base_vals = [
        scores_base["macro"],
        scores_base["geo"],
        scores_base["governance"],
        scores_base["finanz"],
        scores_base["sozial"],
    ]
    live_vals = [
        scores_live["macro"],
        scores_live["geo"],
        scores_live["governance"],
        scores_live["finanz"],
        scores_live["sozial"],
    ]

    base_vals += base_vals[:1]
    live_vals += live_vals[:1]

    angles = np.linspace(0, 2 * np.pi, len(base_vals))

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.set_facecolor("#f7f7f7")

    # Gitter
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])

    # Baseline
    ax.plot(angles, base_vals, color="#999999", linewidth=2, label="Baseline")
    ax.fill(angles, base_vals, color="#999999", alpha=0.15)

    # Live
    ax.plot(angles, live_vals, color="#0077cc", linewidth=2, label="Aktuell")
    ax.fill(angles, live_vals, color="#0077cc", alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    ax.set_title(title, fontsize=14, pad=20)
    ax.text(
        0.5, 1.10,
        "Δ = Live – Baseline (5D Risiko-Komponenten)",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
    )
    
    ax.legend(loc="upper right")

    fig.tight_layout()
    plt.close(fig)
    return fig

with gr.Blocks(title="Makro-Simulation") as demo:
    gr.Markdown("# Makro-Simulation")

    # -------------------------------------------------------------
    # Simulation (inkl. Risiko-Output)
    # -------------------------------------------------------------
    with gr.Tab("Simulation"):
        slider_components = []
        half = len(PARAM_SLIDERS) // 2
        with gr.Row():
          # -----------------------------
          # Linke Spalte – erste Hälfte
          # -----------------------------
            with gr.Column(scale=2):
                for key, lo, hi, default in PARAM_SLIDERS[:half]:
                    s = gr.Slider(
                        minimum=lo,
                        maximum=hi,
                        value=default,
                        step=0.01,
                        label=key,
                    )

                    slider_components.append(s)
            # -----------------------------
            # Rechte Spalte – zweite Hälfte
            # -----------------------------
            with gr.Column(scale=2):
                for key, lo, hi, default in PARAM_SLIDERS[half:]:
                    s = gr.Slider(
                        minimum=lo,
                        maximum=hi,
                        value=default,
                        step=0.01,
                        label=key,
                    )

                    slider_components.append(s)

            # -----------------------------
            # Rechte Seitenleiste – Risiko
            # -----------------------------
            with gr.Column(scale=1):
                live_risk_box = gr.JSON(label="Live-Risiko + Parameter")
                risk_thermo = gr.Markdown(label="Risiko-Thermometer")
                live_radar_plot = gr.Plot(label="Live-Radar (5D)")
                delta_radar_plot = gr.Plot(label="Delta-Radar")

        # -----------------------------
        # Buttons + Ergebnisse
        # -----------------------------

        btn_run = gr.Button("Simulation starten")
        summary_text = gr.Textbox(label="Ergebnis-Summary", lines=14)

        early_warning_box = gr.JSON(label="Frühwarnsystem")

        for slider in slider_components:
            slider.change(
                fn=update_live_risk_and_radar,
                inputs=slider_components,
                outputs=[live_risk_box, live_radar_plot, delta_radar_plot, risk_thermo],
            )

        def run_simulation_with_warning(*vals):
            params = _collect_params_from_values(list(vals))
            sim = simulate_with_risk(*vals)
            warning = build_early_warning(params)
            return sim, warning

        btn_run.click(
            fn=run_simulation_with_warning,
            inputs=slider_components,
            outputs=[summary_text, early_warning_box],
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
            outputs=[
                *slider_components,   # alle Slider
                preset_status,        # Status-Text
                live_risk_box,        # JSON
                live_radar_plot,      # Plot
                delta_radar_plot,     # Plot
                risk_thermo,          # Markdown
            ],
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
    # Preset-Diagnose (Tabelle + Heatmap + Balken)
    # -------------------------------------------------------------
    with gr.Tab("Preset-Diagnose"):
        gr.Markdown("### Diagnose der Slider-Presets")

        btn_validate = gr.Button("Risiko-Analyse aktualisieren")
        diag_table = gr.Markdown()
        heatmap_plot = gr.Plot()
        bar_plot = gr.Plot()

        def run_diagnostics():
            errors_by_preset = validate_all_slider_presets()
            table_md, fig_heat, fig_bar = build_risk_tables_and_figures()

            if errors_by_preset:
                lines = [table_md, "\n\n⚠️ Strukturelle Probleme bei folgenden Presets:"]
                for name, errs in errors_by_preset.items():
                    lines.append(f"- **{name}**")
                    for e in errs:
                        lines.append(f"    - {e}")
                final_md = "\n".join(lines)
            else:
                final_md = table_md + "\n\n✅ Alle Slider-Presets sind strukturell gültig."

            return final_md, fig_heat, fig_bar

        btn_validate.click(
            fn=run_diagnostics,
            inputs=None,
            outputs=[diag_table, heatmap_plot, bar_plot],
        )

    # -------------------------------------------------------------
    # Lexikon
    # -------------------------------------------------------------
    with gr.Tab("Lexikon"):
        gr.Markdown(lexikon_erweitert_markdown())


    # -------------------------------------------------------------
    # Langfrist-Prognose (Deterministisch + Stochastisch + MC)
    # -------------------------------------------------------------
    with gr.Tab("Langfrist-Prognose (20 Jahre)"):
        gr.Markdown("### Langfristige Projektion auf Basis der aktuellen Parameter")
        scenario_dropdown = gr.Dropdown(
            choices=["Baseline", "Optimistisch", "Pessimistisch", "Stress"],
            value="Baseline",
            label="Szenario",
        )

        shock_year = gr.Slider(
            minimum=0, maximum=50, value=5, step=1, label="Schockjahr (0 = kein Schock)"
        )

        shock_intensity = gr.Slider(
            minimum=0.0, maximum=0.5, value=0.0, step=0.05, label="Schock-Intensität"
        )

        years_slider = gr.Slider(5, 50, value=20, step=1, label="Prognose-Horizont (Jahre)")
        mc_runs_slider = gr.Slider(1, 200, value=100, step=1, label="Monte-Carlo Durchläufe")

        btn_forecast = gr.Button("Prognose starten")

        shock_list = gr.Dataframe(
            headers=["Jahr", "Typ", "Intensität"],
            datatype=["number", "str", "number"],
            row_count=3,
            column_count=3,
            label="Schock-Events",
        )

        # --- TAB A ---
        with gr.Tab("A – Klassisch-ökonomisch"):
            a_plot1 = gr.Plot(label="BIP-Wachstum (deterministisch vs. stochastisch)")
            a_plot2 = gr.Plot(label="Inflation (deterministisch vs. stochastisch)")
            a_plot3 = gr.Plot(label="Risiko-Drift")
            a_plot4 = gr.Plot(label="Resilienz")
            a_summary = gr.JSON(label="Summary A")
            a_comment = gr.Markdown(label="Kommentar A")   # NEU

        # --- TAB B ---
        with gr.Tab("B – Geopolitisch-ökonomisch"):
            b_plot1 = gr.Plot(label="Importkosten-Multiplikator")
            b_plot2 = gr.Plot(label="Sanktions-Risiko-Proxy")
            b_plot3 = gr.Plot(label="Alternativnetz-Abdeckung")
            b_plot4 = gr.Plot(label="Währungsdiversifikation (heuristisch)")
            b_summary = gr.JSON(label="Summary B")
            b_comment = gr.Markdown(label="Kommentar B")   # NEU

        # --- TAB C ---
        with gr.Tab("C – Systemisch-komplex"):
            c_plot1 = gr.Plot(label="System-Volatilität")
            c_plot2 = gr.Plot(label="Schock-Propagation")
            c_plot3 = gr.Plot(label="Governance-Stabilität (invertiertes Risiko)")
            c_plot4 = gr.Plot(label="Stress-Index")
            c_summary = gr.JSON(label="Summary C")
            c_comment = gr.Markdown(label="Kommentar C")   # NEU

        # --- TAB D ---
        with gr.Tab("D – Vollmodell (Monte-Carlo)"):
            d_plot1 = gr.Plot(label="BIP-Wachstum – Monte-Carlo-Fächer")
            d_plot2 = gr.Plot(label="Inflation – Monte-Carlo-Fächer")
            d_plot3 = gr.Plot(label="Resilienz – Monte-Carlo-Fächer")
            d_plot4 = gr.Plot(label="Risiko-Drift – Monte-Carlo-Fächer")
            d_summary = gr.JSON(label="Summary D")
            d_comment = gr.Markdown(label="Kommentar D")   # NEU

        # --- Kollaps-Alarm (NEU, SAUBER) ---
        alarm_box = gr.Markdown(label="Kollaps‑Alarm")


        def parse_shocks(df, years):
            events = {}
            if df is None:
                return events

            for row in df:
                try:
                    year = int(row[0])
                    typ = row[1]
                    intensity = float(row[2])
                except:
                    continue

                if not (0 <= year < years):
                    continue

                if year not in events:
                    events[year] = {}

                if typ == "Makro-Schock":
                    events[year]["macro_risk_add"] = intensity
                elif typ == "Geo-Schock":
                    events[year]["geo_risk_add"] = intensity
                elif typ == "Resilienz-Schock":
                    events[year]["resilienz_add"] = -intensity
                elif typ == "Volatilitäts-Schock":
                    events[year]["shock_add"] = intensity

            return events



        # ---------------------------------------------------------
        # Forecast-Funktion
        # ---------------------------------------------------------
        def run_forecast(*vals):
            slider_vals = vals[:NUM_SLIDERS]
            years = int(vals[NUM_SLIDERS])
            mc_runs = int(vals[NUM_SLIDERS + 1])
            scenario = vals[NUM_SLIDERS + 2]
            shock_year = int(vals[NUM_SLIDERS + 3])
            shock_intensity = float(vals[NUM_SLIDERS + 4])
            shock_df = vals[NUM_SLIDERS + 5]

            # Events parsen
            events = parse_shocks(shock_df, years)
            if shock_intensity > 0 and 0 <= shock_year < years:
                events[shock_year] = {"shock_add": shock_intensity}

            params = _collect_params_from_values(list(slider_vals))
            params_scenario = apply_scenario(params, scenario)

            det, stoch, mc = simulate_paths(params_scenario, years, mc_runs, events=events)
            scores = compute_risk_scores(params)
            cat, _ = risk_category(scores["total"])
            t = np.arange(years)

            # --- A ---
            fig_a1, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, det["gdp_growth"])
            ax.plot(t, stoch["gdp_growth"], alpha=0.7)
            plt.tight_layout()
            plt.close(fig_a1)

            fig_a2, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, det["inflation"])
            ax.plot(t, stoch["inflation"], alpha=0.7)
            plt.tight_layout()
            plt.close(fig_a2)

 
            fig_a3, ax_a3 = plt.subplots(figsize=(5, 3))
            ax_a3.plot(t, det["risk_drift"], label="deterministisch")
            ax_a3.plot(t, stoch["risk_drift"], label="stochastisch", alpha=0.7)
            ax_a3.set_title("Risiko-Drift")
            ax_a3.set_xlabel("Jahre")
            ax_a3.text(
                0.5, 1.12,
                "Formel: Risk Drift = f(Makro, Geo, Governance, Schocks)",
                transform=ax_a3.transAxes,
                ha="center",
                va="center",
                fontsize=8,
            )
            ax_a3.legend()
            plt.tight_layout()   
            plt.close(fig_a3)

            fig_a4, ax_a4 = plt.subplots(figsize=(5, 3))
            ax_a4.plot(t, det["resilienz"])
            ax_a4.plot(t, stoch["resilienz"], alpha=0.7)
            ax_a4.set_title("Risiko-Drift – Szenarien")
            alarm_text = collapse_alarm(det)
            ax_a4.text(
                0.5, -0.25,
                f"Kollaps-Alarm: {alarm_text}",
                transform=ax_a4.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="red",
            )
            plt.tight_layout()
            plt.close(fig_a4)

            summary_a = {
                "final_gdp_growth_det": det["gdp_growth"][-1],
                "final_inflation_det": det["inflation"][-1],
                "final_resilienz_det": det["resilienz"][-1],
                "final_risk_det": det["risk_drift"][-1],
            }
            comment_a = build_comment_a(summary_a)

            # --- B ---
            fig_b1, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, det["importkosten_mult"])
            plt.tight_layout()
            plt.close(fig_b1)

            fig_b2, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, [scores["geo"]] * years)
            plt.tight_layout()
            plt.close(fig_b2)

            fig_b3, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, [params["Alternativnetz_Abdeckung"]] * years)
            plt.tight_layout()
            plt.close(fig_b3)

            fig_b4, ax = plt.subplots(figsize=(5, 3))
            divers = 1.0 - abs(params["USD_Dominanz"] - params["RMB_Akzeptanz"])
            ax.plot(t, [divers] * years)
            plt.tight_layout()
            plt.close(fig_b4)

            summary_b = {
                "geo_risk": scores["geo"],
                "alternativnetz_abdeckung": params["Alternativnetz_Abdeckung"],
                "waehrungsdiversifikation": divers,
                "final_importkosten_mult_det": det["importkosten_mult"][-1],
            }
            comment_b = build_comment_b(summary_b)

            # --- C ---
            fig_c1, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, det["system_vol"])
            plt.tight_layout()
            plt.close(fig_c1)

            fig_c2, ax = plt.subplots(figsize=(5, 3))
            schock_durchl = scores["geo"] * 0.7 + scores["macro"] * 0.3
            ax.plot(t, [schock_durchl] * years)
            plt.tight_layout()
            plt.close(fig_c2)

            fig_c3, ax = plt.subplots(figsize=(5, 3))
            gov_stab = 1.0 - scores["governance"]
            ax.plot(t, [gov_stab] * years)
            plt.tight_layout()
            plt.close(fig_c3)

            fig_c4, ax = plt.subplots(figsize=(5, 3))
            ax.plot(t, det["stress_index"])
            ax.plot(t, stoch["stress_index"], alpha=0.7)
            plt.tight_layout()
            plt.close(fig_c4)

            summary_c = {
                "system_vol_det": det["system_vol"][0],
                "schock_propagation_proxy": schock_durchl,
                "governance_stability_proxy": gov_stab,
                "final_stress_det": det["stress_index"][-1],
            }
            comment_c = build_comment_c(summary_c)

            # --- D ---
            fig_d1 = build_fan_plot(mc["gdp_growth"], years, "BIP-Wachstum – MC")
            fig_d2 = build_fan_plot(mc["inflation"], years, "Inflation – MC")
            fig_d3 = build_fan_plot(mc["resilienz"], years, "Resilienz – MC")
            fig_d4 = build_fan_plot(mc["risk_drift"], years, "Risiko-Drift – MC")

            summary_d = {
                "gdp_growth_mean_final": float(np.mean([run[-1] for run in mc["gdp_growth"]])),
                "inflation_mean_final": float(np.mean([run[-1] for run in mc["inflation"]])),
                "resilienz_mean_final": float(np.mean([run[-1] for run in mc["resilienz"]])),
                "risk_drift_mean_final": float(np.mean([run[-1] for run in mc["risk_drift"]])),
            }
            comment_d = build_comment_d(summary_d)

            return (
                fig_a1, fig_a2, fig_a3, fig_a4, summary_a, comment_a,
                fig_b1, fig_b2, fig_b3, fig_b4, summary_b, comment_b,
                fig_c1, fig_c2, fig_c3, fig_c4, summary_c, comment_c,
                fig_d1, fig_d2, fig_d3, fig_d4, summary_d, comment_d,
                alarm_text,
            )

        # Button-Handler
        btn_forecast.click(
            fn=run_forecast,
            inputs=slider_components + [
                years_slider, mc_runs_slider, scenario_dropdown,
                shock_year, shock_intensity, shock_list
            ],
            outputs=[
                a_plot1, a_plot2, a_plot3, a_plot4, a_summary, a_comment,
                b_plot1, b_plot2, b_plot3, b_plot4, b_summary, b_comment,
                c_plot1, c_plot2, c_plot3, c_plot4, c_summary, c_comment,
                d_plot1, d_plot2, d_plot3, d_plot4, d_summary, d_comment,
                alarm_box,
            ],
        )

        with gr.Tab("Vergleich"):
            gr.Markdown("### Länder-Vergleich")

            presets = load_presets()
            choices = list(presets.keys())

            land_a = gr.Dropdown(choices=choices, label="Land A")
            land_b = gr.Dropdown(choices=choices, label="Land B")

            btn_compare = gr.Button("Vergleich starten")

            radar_a = gr.Plot(label="Radar A")
            radar_b = gr.Plot(label="Radar B")
            compare_table = gr.JSON(label="Risiko-Vergleich")
            compare_comment = gr.Markdown(label="Kommentar Vergleich")

            def compare_countries(a, b):
                presets = load_presets()
                pa = presets.get(a)
                pb = presets.get(b)

                # Risiko-Scores berechnen
                sa = compute_risk_scores(pa)
                sb = compute_risk_scores(pb)

                # 5D-Radar direkt aus Scores
                fig_a = build_risk_radar_5d(sa, f"Risiko-Radar 5D: {a}")
                fig_b = build_risk_radar_5d(sb, f"Risiko-Radar 5D: {b}")

                table = {
                    "Land A": sa,
                    "Land B": sb,
                }

                def interpret(sa, sb):
                    txt = []
                    if sa["total"] < sb["total"]:
                        txt.append(f"**{a}** weist ein geringeres Gesamtrisiko auf als **{b}**.")
                    elif sa["total"] > sb["total"]:
                        txt.append(f"**{b}** weist ein geringeres Gesamtrisiko auf als **{a}**.")
                    else:
                        txt.append("Beide Länder liegen beim Gesamtrisiko etwa gleichauf.")

                    if sa["macro"] > sb["macro"]:
                        txt.append(f"Makro-Risiko ist in **{a}** höher als in **{b}**.")
                    elif sa["macro"] < sb["macro"]:
                        txt.append(f"Makro-Risiko ist in **{b}** höher als in **{a}**.")

                    if sa["geo"] != sb["geo"]:
                        txt.append("Geopolitische Risiken unterscheiden sich spürbar; Details siehe Radar.")

                    return " ".join(txt)

                comment = interpret(sa, sb)
                return fig_a, fig_b, table, comment


            btn_compare.click(
                fn=compare_countries,
                inputs=[land_a, land_b],
                outputs=[radar_a, radar_b, compare_table, compare_comment],
            )


    def run_scenario_dashboard(*vals):
        slider_vals = vals[:NUM_SLIDERS]
        years = int(vals[NUM_SLIDERS])
        mc_runs = int(vals[NUM_SLIDERS + 1])

        base_params = _collect_params_from_values(list(slider_vals))

        scenario_results = {}

        for scen in SCENARIOS:
            p = apply_scenario(base_params, scen)
            det, stoch, mc = simulate_paths(p, years, mc_runs)

            scenario_results[scen] = {
                "gdp": det["gdp_growth"],
                "inf": det["inflation"],
                "res": det["resilienz"],
                "risk": det["risk_drift"],
            }

        t = np.arange(years)
        # GDP plot
        fig_gdp, ax = plt.subplots(figsize=(6, 4))
        for scen in SCENARIOS:
            ax.plot(t, scenario_results[scen]["gdp"], label=scen)
        ax.set_title("BIP-Wachstum – Szenarien")
        ax.legend()
        plt.tight_layout()

        # Inflation
        fig_inf, ax2 = plt.subplots(figsize=(6, 4))
        for scen in SCENARIOS:
            ax2.plot(t, scenario_results[scen]["inf"], label=scen)
        ax2.set_title("Inflation – Szenarien")
        ax2.legend()
        plt.tight_layout()

        # Resilienz
        fig_res, ax3 = plt.subplots(figsize=(6, 4))
        for scen in SCENARIOS:
            ax3.plot(t, scenario_results[scen]["res"], label=scen)
        ax3.set_title("Resilienz – Szenarien")
        ax3.legend()
        plt.tight_layout()

        # Risiko
        fig_risk, ax4 = plt.subplots(figsize=(6, 4))
        for scen in SCENARIOS:
            ax4.plot(t, scenario_results[scen]["risk"], label=scen)
        ax4.set_title("Risiko-Drift – Szenarien")
        ax4.text(
            0.5, 1.12,
            "Formel: Risk Drift = f(Makro, Geo, Governance, Schocks)",
            transform=ax4.transAxes,
            ha="center",
            va="center",
            fontsize=8,
        )
        ax4.legend()
        plt.tight_layout()

        # Kommentar
        comment = (
            "### Interpretation\n"
            "- **Optimistisch**: bessere Governance, höhere Resilienz, geringere Risiken.\n"
            "- **Pessimistisch**: höhere Risiken, geringere Resilienz, schwächeres Wachstum.\n"
            "- **Stress**: starke Volatilität, Risikoanstieg, deutliche Wachstumsdämpfung.\n"
        )

        return fig_gdp, fig_inf, fig_res, fig_risk, comment

    with gr.Tab("Szenario-Dashboard"):
        gr.Markdown("### Vergleich der Szenarien (Baseline, Optimistisch, Pessimistisch, Stress)")

        years_sd = gr.Slider(5, 50, value=20, step=1, label="Jahre")
        mc_sd = gr.Slider(1, 200, value=50, step=1, label="Monte-Carlo Durchläufe")

        btn_sd = gr.Button("Szenarien simulieren")

        sd_plot_gdp = gr.Plot(label="BIP-Wachstum – Szenarien")
        sd_plot_inf = gr.Plot(label="Inflation – Szenarien")
        sd_plot_res = gr.Plot(label="Resilienz – Szenarien")
        sd_plot_risk = gr.Plot(label="Risiko-Drift – Szenarien")

        sd_comment = gr.Markdown(label="Kommentar")

        # WICHTIG: Button-Handler MUSS HIER stehen
        btn_sd.click(
            fn=run_scenario_dashboard,
            inputs=slider_components + [years_sd, mc_sd],
            outputs=[sd_plot_gdp, sd_plot_inf, sd_plot_res, sd_plot_risk, sd_comment],
        )

if __name__ == "__main__":
    demo.launch()
