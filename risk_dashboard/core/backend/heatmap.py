# core/backend/heatmap.py

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from core.data.assets import fetch_price_history, safe_rename

def correlation_matrix(symbols):
    frames = []
    for s in symbols:
        series = fetch_price_history(s)
        if series is None:
            continue
        # pct_change + robustes Rename
        renamed = safe_rename(series.pct_change(), s)
        if renamed is not None:
            frames.append(renamed)

    if not frames:
        return None

    df = pd.concat(frames, axis=1).dropna()
    return df.corr()

def plot_correlation_heatmap(symbols):
    corr = correlation_matrix(symbols)
    if corr is None:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
    ax.set_title("Korrelation‑Matrix")
    return fig
