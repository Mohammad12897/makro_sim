# ui/components.py

import plotly.graph_objects as go
import gradio as gr
from core.lexicon import load_lexicon


# ---------------------------------------------------------
# Radar-Plot für ein einzelnes Land (mit Tooltips, Farben, Ring, Legende)
# ---------------------------------------------------------

def make_radar_plot(scores: dict, title: str = "Radar") -> go.Figure:
    """
    Erstellt einen Radar-Plot für ein einzelnes Land.
    0 = geringes Risiko (gut), 1 = hohes Risiko (schlecht).
    Mit:
    - Lexikon-Tooltips
    - Risiko-Farbskala (grün/gelb/rot)
    - Ø-Risiko-Ring
    - Farblegende
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

    # Ø-Risiko (ohne den duplizierten letzten Punkt)
    avg_risk = sum(values[:-1]) / len(values[:-1])

    # Lexikon laden
    lex = load_lexicon()
    tooltips = [lex.get(dim, "") for dim in dims]
    tooltips.append(tooltips[0])

    # Risiko-Farben
    def risk_color(v):
        if v < 0.33:
            return "green"
        elif v < 0.66:
            return "gold"
        else:
            return "red"

    colors = [risk_color(v) for v in values]

    fig = go.Figure()

    # Haupt-Radar
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels + [labels[0]],
        fill='toself',
        name=title,
        line=dict(color="black", width=2),
        marker=dict(color=colors, size=12),
        customdata=tooltips,
        hovertemplate="<b>%{theta}</b><br>Wert: %{r}<br><br>%{customdata}"
    ))

    # Ø-Risiko-Ring
    fig.add_trace(go.Scatterpolar(
        r=[avg_risk] * len(values),
        theta=labels + [labels[0]],
        mode="lines",
        line=dict(color="black", width=1, dash="dot"),
        name=f"Ø Risiko: {avg_risk:.2f}"
    ))

    # Farblegende
    fig.add_trace(go.Scatterpolar(
        r=[None], theta=[None],
        mode="markers",
        marker=dict(size=12, color="green"),
        name="Niedriges Risiko (0–0.33)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[None], theta=[None],
        mode="markers",
        marker=dict(size=12, color="gold"),
        name="Mittleres Risiko (0.33–0.66)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[None], theta=[None],
        mode="markers",
        marker=dict(size=12, color="red"),
        name="Hohes Risiko (0.66–1)"
    ))

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=["0", "0.25", "0.5", "0.75", "1"],
                title="Risiko (0 = gering, 1 = hoch)"
            )
        ),
        showlegend=True,
        height=600
    )

    return fig


# ---------------------------------------------------------
# Multi-Radar-Vergleich
# ---------------------------------------------------------

def make_multi_radar_plot(score_list):
    """
    score_list = [(country, scores), ...]
    Multi-Radar-Vergleich mit Lexikon-Tooltips und Achsenbeschriftung.
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

    lex = load_lexicon()
    tooltips = [lex.get(dim, "") for dim in dims]
    tooltips.append(tooltips[0])

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
                range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=["0", "0.25", "0.5", "0.75", "1"],
                title="Risiko (0 = gering, 1 = hoch)"
            )
        ),
        showlegend=True,
        height=650
    )

    return fig


# ---------------------------------------------------------
# Delta-Radar (Vorher/Nachher)
# ---------------------------------------------------------

def make_delta_radar_plot(base_scores, scenario_scores, title="Delta-Radar"):
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

    base = [base_scores[d] for d in dims]
    scen = [scenario_scores[d] for d in dims]

    base.append(base[0])
    scen.append(scen[0])

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=base,
        theta=labels + [labels[0]],
        fill='none',
        name="Vorher",
        line=dict(color="gray", width=2)
    ))

    fig.add_trace(go.Scatterpolar(
        r=scen,
        theta=labels + [labels[0]],
        fill='toself',
        name="Nachher",
        line=dict(color="red", width=3)
    ))

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=["0", "0.25", "0.5", "0.75", "1"],
                title="Risiko (0 = gering, 1 = hoch)"
            )
        ),
        showlegend=True,
        height=600
    )

    return fig


# ---------------------------------------------------------
# Heatmap-Radar
# ---------------------------------------------------------

def make_heatmap_radar(scores, title="Heatmap-Radar"):
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

    values = [scores[d] for d in dims]
    values.append(values[0])

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels + [labels[0]],
        fill='toself',
        mode="lines",
        line=dict(color="black", width=1),
        marker=dict(
            color=values,
            colorscale="RdYlGn_r",  # grün → gelb → rot
            size=12,
            colorbar=dict(title="Risiko")
        ),
        name=title
    ))

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=["0", "0.25", "0.5", "0.75", "1"],
                title="Risiko (0 = gering, 1 = hoch)"
            )
        ),
        showlegend=False,
        height=600
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
