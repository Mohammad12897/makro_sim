# core/cluster.py

from __future__ import annotations
from typing import Dict, List
import numpy as np
from sklearn.cluster import KMeans

from core.risk_model import compute_risk_scores


# ---------------------------------------------------------
# Hilfsfunktion: Extrahiert die relevanten Risiko-Dimensionen
# ---------------------------------------------------------

CLUSTER_DIMS = [
    "macro",
    "geo",
    "governance",
    "handel",
    "supply_chain",
    "financial",
    "tech",
    "energie",
    "currency",
    "political_security",
    "strategische_autonomie"
]


def extract_vector(scores: dict) -> np.ndarray:
    """
    Extrahiert die Risiko-Dimensionen als Vektor für das Clustering.
    """
    return np.array([scores[d] for d in CLUSTER_DIMS], dtype=float)


# ---------------------------------------------------------
# Cluster-Berechnung
# ---------------------------------------------------------

def cluster_risk_dimensions(presets: Dict[str, dict], k: int = 3):
    """
    Führt ein K-Means-Clustering über alle Länder durch.
    """
    countries = list(presets.keys())
    vectors = []

    for land in countries:
        scores = compute_risk_scores(presets[land])
        vectors.append(extract_vector(scores))

    X = np.vstack(vectors)

    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)

    result = {country: int(label) for country, label in zip(countries, labels)}
    centers = model.cluster_centers_

    return result, centers


# ---------------------------------------------------------
# Cluster-Interpretation
# ---------------------------------------------------------

def interpret_cluster(center: np.ndarray) -> str:
    """
    Liefert eine textuelle Interpretation eines Cluster-Zentrums.
    """
    md = "### Cluster-Interpretation\n"

    dims_sorted = sorted(
        zip(CLUSTER_DIMS, center),
        key=lambda x: x[1],
        reverse=True
    )

    md += "- **Haupttreiber des Risikos:**\n"
    for d, v in dims_sorted[:3]:
        md += f"  - {d}: {v:.2f}\n"

    md += "\n- **Stabilitätsanker:**\n"
    for d, v in dims_sorted[-2:]:
        md += f"  - {d}: {v:.2f}\n"

    md += "\n- **Politische Abhängigkeit & Autonomie:**\n"
    ps = center[CLUSTER_DIMS.index("political_security")]
    sa = center[CLUSTER_DIMS.index("strategische_autonomie")]

    if ps > 0.75:
        md += "  - Sehr hohe politische Abhängigkeit.\n"
    elif ps > 0.55:
        md += "  - Erhöhte politische Abhängigkeit.\n"
    else:
        md += "  - Politische Abhängigkeit moderat.\n"

    if sa > 0.75:
        md += "  - Sehr hohe strategische Autonomie.\n"
    elif sa > 0.50:
        md += "  - Solide strategische Autonomie.\n"
    else:
        md += "  - Eingeschränkte strategische Autonomie.\n"

    return md


# ---------------------------------------------------------
# Cluster-Heatmap
# ---------------------------------------------------------

def cluster_heatmap(presets: Dict[str, dict], k: int = 3):
    """
    Gibt eine Heatmap-Tabelle zurück:
    Land | Cluster | political_security | strategische_autonomie | total
    """
    clusters, _ = cluster_risk_dimensions(presets, k)
    rows = []

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append([
            land,
            clusters[land],
            round(scores["political_security"], 3),
            round(scores["strategische_autonomie"], 3),
            round(scores["total"], 3)
        ])

    return rows
