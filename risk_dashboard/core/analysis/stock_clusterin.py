#core/analysis/stock_clusterin.py
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

def cluster_stocks(rows, n_clusters=3):
    df = pd.DataFrame(rows)

    # Features, die wir clustern wollen
    features = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]

    # Fehlende Spalten automatisch hinzufügen
    for f in features:
        if f not in df.columns:
            df[f] = 0

    # Nur die Features extrahieren
    df_clean = df[features].fillna(0)

    # Normalisieren
    X = StandardScaler().fit_transform(df_clean)

    # KMeans
    kmeans = KMeans(n_clusters=n_clusters, n_init=10)
    df["Cluster"] = kmeans.fit_predict(X)

    return df
