# ui/plots.py

import plotly.graph_objects as go
from core.lexicon import load_lexicon


def plot_radar(scores: dict):
    """
    Erzeugt ein Radar-Diagramm mit Tooltip-Texten aus dem Lexikon.
    """
    dimensions = list(scores.keys())
    values = list(scores.values())

    # Lexikon laden
    lex = load_lexicon()

    # Tooltip-Mapping
    tooltips = {dim: lex.get(dim, "") for dim in dimensions}

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=dimensions,
        fill='toself',
        name='Risiko'
    ))

    # Tooltip aktivieren
    fig.update_traces(
        hovertemplate="<b>%{theta}</b><br>Wert: %{r}<br><br>%{customdata}",
        customdata=[tooltips[dim] for dim in dimensions]
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False
    )

    return fig
