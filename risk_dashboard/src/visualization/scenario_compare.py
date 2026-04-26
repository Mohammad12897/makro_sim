# risk_dashboard/src/visualization/scenario_compare.py
import streamlit as st
import pandas as pd

def plot_scenario_comparison(base: dict, scenario: dict):
    df = pd.DataFrame({
        "Komponente": [
            "Inflation", "Zinsen", "Wachstum",
            "Arbeitsmarkt", "FX", "Marktstress"
        ],
        "Baseline": [
            base["inflation_risk"],
            base["interest_risk"],
            base["growth_risk"],
            base["labor_risk"],
            base["fx_risk"],
            base["market_stress"]
        ],
        "Szenario": [
            scenario["inflation_risk"],
            scenario["interest_risk"],
            scenario["growth_risk"],
            scenario["labor_risk"],
            scenario["fx_risk"],
            scenario["market_stress"]
        ]
    })

    st.bar_chart(df.set_index("Komponente"))