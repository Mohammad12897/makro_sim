# core/cluster.py

from __future__ import annotations
from typing import Dict, List
import numpy as np
from sklearn.cluster import KMeans
import plotly.express as px
import pandas as pd


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

def describe_clusters(presets, clusters):
    """
    Erzeugt ein Markdown-Lexikon für die Cluster-Ergebnisse.
    """
    # Cluster-Mittelwerte berechnen
    cluster_summary = {}
    for land, cid in clusters.items():
        scores = compute_risk_scores(presets[land])
        if cid not in cluster_summary:
            cluster_summary[cid] = {"political_security": [], "strategische_autonomie": [], "total": [], "länder": []}
        cluster_summary[cid]["political_security"].append(scores["political_security"])
        cluster_summary[cid]["strategische_autonomie"].append(scores["strategische_autonomie"])
        cluster_summary[cid]["total"].append(scores["total"])
        cluster_summary[cid]["länder"].append(land)

    # Markdown-Text bauen
    lines = ["# Cluster-Lexikon", ""]
    for cid, vals in cluster_summary.items():
        avg_ps = sum(vals["political_security"]) / len(vals["political_security"])
        avg_aut = sum(vals["strategische_autonomie"]) / len(vals["strategische_autonomie"])
        avg_total = sum(vals["total"]) / len(vals["total"])
        laender = ", ".join(vals["länder"])

        # einfache Beschreibung abhängig von Werten
        if avg_total < 0.33:
            desc = "Niedriges Gesamtrisiko, hohe Stabilität."
        elif avg_total < 0.66:
            desc = "Mittleres Gesamtrisiko, gemischte Stabilität."
        else:
            desc = "Hohes Gesamtrisiko, verwundbare Struktur."

        lines.append(f"## Cluster {cid}")
        lines.append(f"**Beschreibung:** {desc}")
        lines.append(f"**Beispiel-Länder:** {laender}")
        lines.append("")
        lines.append("| Ø Political Security | Ø Autonomie | Ø Total |")
        lines.append("|----------------------|-------------|---------|")
        lines.append(f"| {avg_ps:.2f} | {avg_aut:.2f} | {avg_total:.2f} |")
        lines.append("")

    return "\n".join(lines)


def cluster_risk_dimensions(presets: dict, k: int = 3):
    """
    Teilt Länder anhand ihrer Risiko-Scores in k Cluster ein.
    Gibt ein Dict {Land: Cluster-ID} und das KMeans-Modell zurück.
    """
    X = []
    lands = []
    for land, params in presets.items():
        scores = compute_risk_scores(params)
        X.append([
            scores["political_security"],
            scores["strategische_autonomie"],
            scores["total"]
        ])
        lands.append(land)

    X = np.array(X)

    model = KMeans(n_clusters=k, random_state=42)
    labels = model.fit_predict(X)

    clusters = {land: int(label) for land, label in zip(lands, labels)}
    return clusters, model


def cluster_scatterplot(presets: dict, k: int = 3):
    """
    Erstellt einen Scatterplot: Political Security vs. Strategische Autonomie,
    Farbe = Cluster, Größe = Total-Risiko.
    """
    clusters, _ = cluster_risk_dimensions(presets, k)
    rows = []

    for land, params in presets.items():
        scores = compute_risk_scores(params)
        rows.append({
            "Land": land,
            "Cluster": clusters[land],
            "Political Security": scores["political_security"],
            "Strategische Autonomie": scores["strategische_autonomie"],
            "Total": scores["total"]
        })

    df = pd.DataFrame(rows)

    fig = px.scatter(
        df,
        x="Political Security",
        y="Strategische Autonomie",
        color="Cluster",
        size="Total",
        hover_name="Land",
        title="Cluster-Scatterplot: Länder nach Risiko-Dimensionen"
    )
    fig.update_layout(height=600)
    return fig
