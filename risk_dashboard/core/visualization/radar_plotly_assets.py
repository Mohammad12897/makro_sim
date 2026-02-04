#core/visualization/radar_plotly_assets.py

import plotly.graph_objects as go
import pandas as pd

def plot_asset_radar(rows, mode="einsteiger"):

    df = pd.DataFrame(rows).set_index("symbol")

    # Achsen definieren
    axes = [
        "performance_1y",
        "performance_3y",
        "volatility_90d",
        "sharpe",
        "max_drawdown",
        "trend_sma_ratio",
        "correlation_spy",
        "correlation_gold",
    ]

    # Normalisierung
    df_norm = (df[axes] - df[axes].min()) / (df[axes].max() - df[axes].min())

    fig = go.Figure()

    for symbol in df_norm.index:
        fig.add_trace(go.Scatterpolar(
            r=df_norm.loc[symbol].values,
            theta=axes,
            fill='toself',
            name=symbol
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title="Asset-Radar (ETFs, Aktien, Bitcoin)"
    )

    return fig
