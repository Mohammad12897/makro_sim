#core/analysis/stock_clusterin.py
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

def cluster_stocks(rows):
    df = pd.DataFrame(rows)

    # Features für Clustering
    features = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]

    # Fehlende Spalten automatisch ergänzen
    for f in features:
        if f not in df.columns:
            df[f] = 0

    df_clean = df[features].fillna(0)

    # Anzahl Aktien
    n = len(df_clean)

    # Wenn weniger als 3 Aktien → kein Clustering möglich
    if n < 3:
        df["Cluster"] = "Nicht genug Daten (min. 3 Aktien)"
        return df

    # Anzahl Cluster = min(3, Anzahl Aktien)
    k = min(3, n)

    X = StandardScaler().fit_transform(df_clean)

    kmeans = KMeans(n_clusters=k, n_init=10)
    df["Cluster"] = kmeans.fit_predict(X)

    return df
