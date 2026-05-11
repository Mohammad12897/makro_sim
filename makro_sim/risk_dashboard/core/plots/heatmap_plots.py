import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

def plot_risk_heatmap(presets_all):
    df = pd.DataFrame(presets_all).T
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(df, cmap="coolwarm", annot=False, ax=ax)
    ax.set_title("Risiko‑Heatmap")
    return fig
