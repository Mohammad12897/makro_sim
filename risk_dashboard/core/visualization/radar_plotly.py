# core/visualization/radar_plotly.py
import plotly.graph_objects as go

def plot_radar_plotly(rows):
    metrics = [
        # Mikro
        "1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta",

        # Fundamentaldaten
        "KGV", "KBV", "KUV", "DivRendite %",

        # Makro
        "BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote"
    ]

    fig = go.Figure()

    for r in rows:
        values = [r.get(m + " norm", 0) for m in metrics]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=r.get("name", r.get("ticker", "Unknown")),
            hovertemplate="<b>%{text}</b><br>%{r}<extra></extra>",
            text=[r.get("name", r.get("ticker", ""))] * len(metrics)
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=600
    )

    return fig
