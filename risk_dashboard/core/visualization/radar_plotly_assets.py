#core/visualization/radar_plotly_assets.py
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def plot_asset_radar(rows, mode="einsteiger"):

    df = pd.DataFrame(rows).set_index("symbol")

    # Schritt 1: Achsen sammeln, die überhaupt existieren
    available_axes = set()
    for row in rows:
        for key, value in row.items():
            if key != "symbol" and value is not None and not pd.isna(value):
                available_axes.add(key)

    # Schritt 2: Achsen behalten, die bei ALLEN Assets existieren
    common_axes = []
    for axis in available_axes:
        if all(axis in row and row[axis] is not None and not pd.isna(row[axis]) for row in rows):
            common_axes.append(axis)

    if not common_axes:
        raise ValueError("Keine gemeinsamen Achsen für Radar gefunden.")

    # Schritt 3: DataFrame auf gemeinsame Achsen reduzieren
    df = df[common_axes]

    # Schritt 4: Spalten entfernen, die komplett NaN sind
    df = df.dropna(axis=1, how="all")

    if df.empty:
        raise ValueError("Alle Achsen enthalten nur NaN-Werte.")

    # Schritt 5: Normalisierung robust durchführen
    min_vals = df.min()
    max_vals = df.max()

    # Verhindert Division durch 0
    ranges = max_vals - min_vals
    ranges = ranges.replace(0, 1e-9)

    df_norm = (df - min_vals) / ranges

    fig = go.Figure()

    for symbol in df_norm.index:
        fig.add_trace(go.Scatterpolar(
            r=df_norm.loc[symbol].values,
            theta=df_norm.columns,
            fill='toself',
            name=symbol
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title="Asset-Radar (ETFs, Aktien, Bitcoin)"
    )

    return fig
