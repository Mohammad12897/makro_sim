import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def ui_portfolio_studio(ticker_text):
    # -----------------------------
    # 1. Ticker-Liste parsen
    # -----------------------------
    tickers = [t.strip() for t in ticker_text.split(",") if t.strip()]

    if not tickers:
        return plt.figure(), pd.DataFrame([["Keine Ticker angegeben"]], columns=["Info"])

    # -----------------------------
    # 2. Kursdaten laden
    # -----------------------------
    price_data = {}
    for t in tickers:
        series = fetch_price_history(t, period="1y")
        if series is None or len(series) == 0:
            return plt.figure(), pd.DataFrame([[f"Keine Daten für {t}"]], columns=["Info"])
        price_data[t] = series

    df = pd.DataFrame(price_data)

    # -----------------------------
    # 3. Performance berechnen
    # -----------------------------
    perf = df / df.iloc[0]  # normiert auf 1

    # -----------------------------
    # 4. Kennzahlen berechnen
    # -----------------------------
    returns = df.pct_change().dropna()

    stats = pd.DataFrame({
        "Rendite (p.a.)": returns.mean() * 252,
        "Volatilität (p.a.)": returns.std() * np.sqrt(252),
        "Max Drawdown": (perf / perf.cummax() - 1).min()
    })

    # -----------------------------
    # 5. Performance-Plot
    # -----------------------------
    fig, ax = plt.subplots(figsize=(7, 4))
    perf.plot(ax=ax)
    ax.set_title("Portfolio‑Performance (normiert)")
    ax.set_ylabel("Wert (Start = 1)")
    ax.grid(True)

    return fig, stats

def ui_portfolio_optimizer(ticker_text):
    """
    Portfolio‑Optimierung (Mean‑Variance)
    """
    try:
        tickers = [t.strip() for t in ticker_text.split(",") if t.strip()]
        data = {}

        for t in tickers:
            series = fetch_price_history(t, period="1y")
            if series is not None:
                data[t] = series

        df = pd.DataFrame(data).dropna()
        returns = df.pct_change().dropna()

        # Kovarianzmatrix
        cov = returns.cov() * 252
        mean_ret = returns.mean() * 252

        # Optimierung (Minimum Variance)
        inv_cov = np.linalg.inv(cov)
        weights = inv_cov.sum(axis=1) / inv_cov.sum().sum()

        weight_df = pd.DataFrame({
            "Ticker": tickers,
            "Gewichtung": weights
        })

        fig = plot_efficient_frontier(mean_ret, cov)

        return weight_df, fig

    except Exception as e:
        return pd.DataFrame([["Fehler", str(e)]]), None
