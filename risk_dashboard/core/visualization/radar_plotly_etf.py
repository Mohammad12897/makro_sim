# core/visualization/radar_plotly_etf.py
import plotly.graph_objects as go
from core.visualization.lexicon import get_tooltip_map_for_tab


def _ampel_color(value: float) -> str:
    if value >= 0.66:
        return "green"
    if value >= 0.33:
        return "orange"
    return "red"


def plot_etf_radar(rows, mode="einsteiger"):
    all_metrics = [
        "1Y %", "5Y %", "Volatilität %", "Sharpe",
        "TER", "Tracking Error", "AUM", "DivRendite %"
    ]

    if mode == "einsteiger":
        metrics = ["1Y %", "Volatilität %", "TER", "DivRendite %"]
    else:
        metrics = all_metrics

    tooltip_map = get_tooltip_map_for_tab("etf", mode)

    fig = go.Figure()

    for r in rows:
        values = [r.get(m + " norm", 0) for m in metrics]
        name = r.get("name", r.get("ticker", "ETF"))

        marker_colors = [_ampel_color(v) for v in values]
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
