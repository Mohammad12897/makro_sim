import matplotlib.pyplot as plt
import pandas as pd
def plot_summary(summary: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6,3))
    df_plot = summary[["p05","median","p95"]].transpose()
    df_plot.plot(kind="bar", ax=ax, color=["#82B1FF","#2962FF","#0039CB"])
    ax.set_title("Makro-Metriken p05 / median / p95"); ax.set_ylabel("Wert")
    plt.tight_layout(); plt.close(fig); return fig
def plot_years(df, title="Mehrjahres-Simulation"):
    fig, ax = plt.subplots(figsize=(8,4)); df_plot = df.set_index("Jahr"); df_plot.plot(ax=ax, marker="o")
    ax.set_title(title); ax.set_ylabel("Wert"); ax.grid(alpha=0.3); plt.tight_layout(); plt.close(fig); return fig
