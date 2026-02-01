# core/visualization/radar_plotly.py
import plotly.graph_objects as go

def plot_radar_plotly(rows):
    if not rows:
        return None

    metrics = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]

    fig = go.Figure()

    for r in rows:
        values = [r.get(m, 0) for m in metrics]
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=r.get("ticker", "Unknown"),
            hovertemplate="<b>%{text}</b><br>%{r}<extra></extra>",
            text=[r.get("ticker", "")] * len(metrics)
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        height=600
    )

    return fig
