<<<<<<< HEAD
#core/cluster_engine.py
=======
#risk_dashboard/core/cluster_engine.py
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
from sklearn.cluster import KMeans
import pandas as pd

def compute_clusters(presets_all, k=3):
    df = pd.DataFrame(presets_all).T
    model = KMeans(n_clusters=k, n_init="auto")
    labels = model.fit_predict(df)
    df["cluster"] = labels
    return df
