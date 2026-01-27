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



/content/makro_sim/risk_dashboard
│
├── core/
│   ├── portfolio_sim/
│   │   ├── covariance.py
│   │   ├── mc_engine.py
│   │   ├── risk_metrics.py
│   │   ├── scenario_adapter.py
│   │   └── portfolio_model.py
│   ├── data_import.py
│   ├── covariance.py
│   ├── mc_simulator.py
│   ├── portfolio.py
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
│   ├── equity_returns.csv
│   ├── bond_returns.csv
│   ├── gold_returns.csv
│   ├── slider_presets.json
│   ├── scenario_presets.json
│   └── lexicon.json
│
│
├── assets/
│   └── icons/
├── docs/
│
├── test/
│   ├── app.py
│   └── example_presets.py
├── tests/
│   ├── test_mc_engine.py
│   ├── test_risk_metrics.py
│   ├── test_covariance.py
│   ├── test_scenario_adapter.py
│   └── conftest.py
│
├── pytest.ini
├── requirements.txt
└── main.py

risk_dashboard/
│
├── main.py
│
├── ui/
│   ├── __init__.py
│   └── app.py
│
├── core/
│   ├── __init__.py
│   ├── presets.py
│   ├── scenario_engine.py
│   ├── risk_engine.py
│   ├── shock_mapping.py
│   ├── utils.py
│   └── ...
│
├── portfolio_sim/
│   ├── __init__.py
│   ├── mc_engine.py          ← deaktiviert
│   └── scenario_compare.py   ← MC-frei
│
└── data/
    └── slider_presets.json
