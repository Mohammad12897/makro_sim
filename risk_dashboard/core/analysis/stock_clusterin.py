import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

def cluster_stocks(rows, n_clusters=3):
    df = pd.DataFrame(rows)

    features = ["1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta"]
    df_clean = df[features].fillna(0)

    X = StandardScaler().fit_transform(df_clean)

    kmeans = KMeans(n_clusters=n_clusters, n_init=10)
    df["Cluster"] = kmeans.fit_predict(X)

    return df
