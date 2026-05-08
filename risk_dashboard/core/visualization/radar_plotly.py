# core/visualization/radar_plotly.py

import plotly.graph_objects as go
from core.visualization.lexicon import get_tooltip_map_for_tab


def _ampel_color(metric: str, value: float) -> str:
    """
    Einfache Ampel-Logik auf Basis des normierten Werts (0–1).
    Grün = gut, Gelb = mittel, Rot = schwach.
    Optional: Kennzahl-spezifische Umkehrlogik.
    """
    # Für Kennzahlen, bei denen "weniger ist besser" (z.B. Volatilität, Drawdown, Arbeitslosenquote),
    # könnte man invertieren – hier bleiben wir bei der Normierung, die du bereits steuerst.
    if value >= 0.66:
        return "green"
    if value >= 0.33:
        return "orange"
    return "red"


def plot_radar_plotly(rows, mode: str = "einsteiger"):
    all_metrics = [
        "1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta",
        "KGV", "KBV", "KUV", "DivRendite %",
        "BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote",
    ]

    if mode == "einsteiger":
        metrics = ["1Y %", "Volatilität %", "KGV", "DivRendite %", "BIP-Wachstum", "Inflation"]
    else:
        metrics = all_metrics

    tooltip_map = get_tooltip_map_for_tab("aktien", mode)

    fig = go.Figure()

    for r in rows:
        values = [r.get(m + " norm", 0) for m in metrics]
        name = f"{r.get('name', r.get('ticker', 'Unknown'))} ({r.get('country', '')})"

        # Farben pro Punkt (Ampel)
        marker_colors = [_ampel_color(m, v) for m, v in zip(metrics, values)]
        customdata = [tooltip_map.get(m, "") for m in metrics]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=name,
            customdata=customdata,
            hovertemplate="<b>%{theta}</b><br>Wert: %{r}<br>%{customdata}<extra></extra>",
            marker=dict(color=marker_colors, size=8),
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=600,
    )

    return fig
