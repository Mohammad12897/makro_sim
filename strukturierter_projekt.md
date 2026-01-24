# Projektstruktur
┌────────────────────────────────┐
│          Inputs                │
│────────────────────────────────│
│ • Standard-Parameter           │
│   (USD_Dominanz, RMB_Akzeptanz,│
│    Zugangsresilienz, Reserven, │
│    FX_Schockempfindlichkeit,   │
│    Sanktions_Exposure,         │
│    Alternativnetz, Liquidität, │
│    CBDC_Nutzung, Golddeckung)  │
│                                │
│ • Erweiterte Parameter         │
│   (Innovation, Fachkräfte,     │
│    Stabilität, Energiepreise,  │
│    Verschuldung)               │
│                                │
│ • Geo-Trigger (Checkboxes)     │
│ • Run Mode (Preview/Full)      │
│ • Adaptive Upscaling (Checkbox)│
│ • Grenzwerte für Ampel-Logik   │
│ • Zeitsimulations-Slider       │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│         Simulation             │
│────────────────────────────────│
│ • Standard-Simulation          │
│ • Erweiterte Simulation        │
│ • Adaptive Summary             │
│ • Szenarien (Batch, Vergleich) │
│ • Marginal-Effekte             │
│ • Impact-Analysen              │
│ • Zeitsimulation (dynamisch)   │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│           Outputs              │
│────────────────────────────────│
│ • Summary-Plot (p05/Median/p95)│
│ • Heatmap (Szenarienvergleich) │
│ • Risiko-Meter (Ampel-Logik)   │
│ • Vergleichstabellen           │
│   - Standard vs Erweitert      │
│   - DeDoll vs USD-Schock       │
│ • Marginal-Effekte (Plot)      │
│ • Impact-Analyse (Plot+Text)   │
│ • Zeitsimulation (Plots+Table) │
│ • Export (CSV)                 │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│              UI                │
│────────────────────────────────│
│ • Gradio Blocks                │
│ • Tabs & Rows für Inputs       │
│ • Buttons für Aktionen         │
│ • Dataframes & Plots für       │
│   Ergebnisse                   │
│ • Markdown-Lexikon (Standard+  │
│   Erweitert)                   │
└────────────────────────────────┘

project_root= /content/makro_sim
project_root/
├─ src/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ etl/
│  │  ├─ __init__.py
│  │  ├─ fetchers.py        # DataAPI, ComtradeAdapter, IMF-Adapter
│  │  ├─ persistence.py     # store_indicator, _write_parquet, DATA_DIR
│  │  └─ transforms.py      # fetch_reserves, helpers
│  ├─ sim/
│  │  ├─ __init__.py
│  │  ├─ core.py            # run_simulation, run_simulation_chunked
│  │  ├─ extended.py        # run_simulation_extended, _compute_bases_extended
│  │  └─ dynamic.py         # simulate_dynamic_years, presets
│  ├─ ui/
│  │  ├─ __init__.py
│  │  └─ gradio_app.py      # Gradio Blocks, callbacks
│  ├─ utils/
│  │  ├─ __init__.py
│  │  ├─ validators.py      # sanitize_params, clamp01, validate_params
│  │  └─ viz.py             # plot_summary, plot_years
│  └─ tests/
│     ├─ test_etl.py
│     ├─ test_sim.py
│     └─ test_integration.py
├─ requirements.txt
├─ README.md
└─ run.py                   # optional: CLI / entrypoint

makro_sim/
├── presets/
│   ├── slider_presets.json        # UI-Presets (flach, direkt für PARAM_SLIDERS)
│   ├── country_presets.json       # Länder-Presets (Indicator-Snapshots, Metadaten)
│   ├── preset_BR.json             # Rohdaten je Land
│   ├── preset_CN.json
│   ├── preset_DE.json
│   ├── preset_FR.json
│   ├── preset_GB.json
│   ├── preset_GR.json
│   ├── preset_IN.json
│   ├── preset_IR.json
│   ├── preset_US.json
├── scripts/
│   ├── merge_country_presets.py   # Merged preset_*.json → country_presets.json
│   ├── generate_slider_presets.py # (optional) Länder → Slider-Presets
├── src/
│   └── ui/
│       └── gradio_app.py          # lädt nur slider_presets.json


risk_dashboard/
│
├── core/
│   ├── risk_model.py
│   ├── scenario_engine.py
│   ├── cluster.py
│   ├── heatmap.py
│   ├── storyline.py
│   ├── ews.py
│   └── utils.py
│
├── ui/
│   ├── app.py
│   ├── components.py
│   └── layout.py
│
├── data/
│   ├── slider_presets.json
│   ├── scenario_presets.json
│   └── texts/
│       ├── radar_text.md
│       ├── storyline_text.md
│       ├── interpretation_text.md
│       └── methodology.md
│
├── assets/
│   └── icons/   (optional)
│
└── main.py

/content/makro_sim/risk_dashboard
│
├── core/
│   ├── risk_model.py
│   ├── scenario_engine.py
│   ├── cluster.py
│   ├── heatmap.py
│   ├── storyline.py
│   ├── ews.py
│   ├── country_assets.py
│   └── utils.py
│
├── ui/
│   ├── app.py
│   ├── components.py
│   └── layout.py
│
├── data/
│   ├── slider_presets.json
│   ├── scenario_presets.json
│   └── texts/
│       ├── radar_text.md
│       ├── storyline_text.md
│       ├── interpretation_text.md
│       └── methodology.md
│
├── assets/
│   └── icons/
├── docs/
│   
│
└── main.py
