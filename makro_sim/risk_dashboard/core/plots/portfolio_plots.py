# core/plots/portfolio_plots.py
import matplotlib.pyplot as plt

def plot_portfolio(portfolio_returns):
    perf = (1 + portfolio_returns).cumprod()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(perf.index, perf.values, color="#1f77b4", linewidth=2.2)
    ax.fill_between(perf.index, perf.values, alpha=0.15, color="#1f77b4")

    ax.set_title("Portfolio Performance (kumuliert)", fontsize=14, pad=15)
    ax.set_ylabel("Wachstumsfaktor")
    ax.set_xlabel("Datum")
    ax.grid(True, linestyle="--", alpha=0.4)

    return fig
