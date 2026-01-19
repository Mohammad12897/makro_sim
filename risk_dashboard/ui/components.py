# ui/components.py

import plotly.graph_objects as go
import gradio as gr
from core.scenario_engine import load_lexicon



# ---------------------------------------------------------
# Radar-Plot für ein einzelnes Land
# ---------------------------------------------------------

def make_radar_plot(scores: dict, title: str = "Radar") -> go.Figure:
    """
    Erstellt einen Radar-Plot für ein einzelnes Land.
    Enthält alle 11 Risiko-Dimensionen + strategische Autonomie.
    Mit Tooltip-Texten aus dem Lexikon.
    """

    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
    ]

    dims = [
        "macro", "geo", "governance", "handel",
        "supply_chain", "financial", "tech", "energie",
        "currency", "political_security", "strategische_autonomie"
    ]

    # Werte extrahieren
    values = [scores[d] for d in dims]
    values.append(values[0])  # Radar schließen

    # Lexikon laden
    lex = load_lexicon()

    # Tooltip-Mapping
    tooltips = [lex.get(dim, "") for dim in dims]
    tooltips.append(tooltips[0])  # Radar schließen

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels + [labels[0]],
        fill='toself',
        name=title,
        line=dict(color="royalblue", width=3),
        customdata=tooltips,
        hovertemplate="<b>%{theta}</b><br>Wert: %{r}<br><br>%{customdata}"
    ))

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=False,
        height=600
    )

    return fig

# ---------------------------------------------------------
# Multi-Radar-Vergleich
# ---------------------------------------------------------

def make_multi_radar_plot(score_list):
    """
    score_list = [(country, scores), ...]
    Multi-Radar-Vergleich mit Tooltip-Texten aus dem Lexikon.
    """
 
    labels = [
        "Makro", "Geo", "Governance", "Handel",
        "Lieferkette", "Finanzen", "Tech", "Energie",
        "Währung", "Politische Abhängigkeit", "Strategische Autonomie"
    ]

    dims = [
        "macro", "geo", "governance", "handel",
        "supply_chain", "financial", "tech", "energie",
        "currency", "political_security", "strategische_autonomie"
    ]

    # Lexikon laden
    lex = load_lexicon()
    tooltips = [lex.get(dim, "") for dim in dims]
    tooltips.append(tooltips[0])  # Radar schließen

    fig = go.Figure()

    colors = [
        "red", "blue", "green", "orange", "purple",
        "brown", "pink", "gray", "cyan", "magenta"
    ]

    for i, (country, scores) in enumerate(score_list):
        values = [scores[d] for d in dims]
        values.append(values[0])

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels + [labels[0]],
            fill='none',
            name=country,
            line=dict(color=colors[i % len(colors)], width=3),
            customdata=tooltips,
            hovertemplate="<b>%{theta}</b><br>%{r}<br><br>%{customdata}"
        ))

    fig.update_layout(
        title="Ländervergleich – Radar",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        height=650
    )

    return fig

# ---------------------------------------------------------
# Dropdown-Komponenten
# ---------------------------------------------------------

def make_country_dropdown(countries):
    return gr.Dropdown(
        choices=countries,
        label="Land auswählen",
        value=countries[0]
    )

def make_scenario_dropdown(scenarios):
    return gr.Dropdown(
        choices=scenarios,
        label="Szenario auswählen",
        value=scenarios[0]
    )

