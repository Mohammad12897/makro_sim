#core/backend/plots.py
import numpy as np
import matplotlib.pyplot as plt

def plot_efficient_frontier(mean_returns, cov_matrix, points=50):
    """
    Zeichnet die Effizienzkurve (Efficient Frontier)
    mean_returns: erwartete Renditen (Series)
    cov_matrix: Kovarianzmatrix (DataFrame)
    """

    num_assets = len(mean_returns)
    results = {"risk": [], "return": []}

    for _ in range(points):
        # Zufällige Gewichte
        weights = np.random.random(num_assets)
        weights /= np.sum(weights)

        # Portfolio-Kennzahlen
        port_return = np.dot(weights, mean_returns)
        port_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        results["risk"].append(port_risk)
        results["return"].append(port_return)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(results["risk"], results["return"], c=results["return"], cmap="viridis")
    ax.set_xlabel("Risiko (Volatilität)")
    ax.set_ylabel("Erwartete Rendite")
    ax.set_title("Effizienzkurve (Efficient Frontier)")

    return fig
