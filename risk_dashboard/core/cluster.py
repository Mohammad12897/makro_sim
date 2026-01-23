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

def cluster_risk_dimensions(presets: dict, k: int = 3):
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

    return clusters, model   # ❗ WICHTIG


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

def describe_clusters(presets, clusters, model):
    centers = model.cluster_centers_  # shape: (k, 3)
    lines = ["# Cluster-Lexikon", ""]

    # Dimensionen extrahieren
    ps_vals = centers[:, 0]   # politisches Risiko
    aut_vals = centers[:, 1]  # strategische Autonomie
    tot_vals = centers[:, 2]  # Gesamtrisiko

    # Hilfsfunktionen für relative Einordnung
    def rel_risk(value, all_values):
        if value == max(all_values):
            return "höchstes"
        elif value == min(all_values):
            return "niedrigstes"
        else:
            return "mittleres"

    def rel_aut(value, all_values):
        if value == max(all_values):
            return "höchste"
        elif value == min(all_values):
            return "geringste"
        else:
            return "mittlere"

    for cid in range(len(centers)):
        ps = ps_vals[cid]
        aut = aut_vals[cid]
        tot = tot_vals[cid]

        laender = [land for land, c in clusters.items() if c == cid]
        laender_str = ", ".join(laender)

        # relative Beschreibungen
        ps_desc = rel_risk(ps, ps_vals) + " politisches Risiko"
        aut_desc = rel_aut(aut, aut_vals) + " strategische Autonomie"
        tot_desc = rel_risk(tot, tot_vals) + " Gesamtrisiko"

        # Cluster-Namen automatisch generieren
        if ps == min(ps_vals) and aut == max(aut_vals):
            cluster_name = "Resiliente, autonome Staaten"
        elif ps == max(ps_vals) and aut == min(aut_vals):
            cluster_name = "Politisch verwundbare, abhängige Staaten"
        elif tot == max(tot_vals):
            cluster_name = "Hochrisiko-Staaten"
        elif tot == min(tot_vals):
            cluster_name = "Niedrigrisiko-Staaten"
        else:
            cluster_name = "Staaten mit gemischtem Risikoprofil"

        # Markdown-Ausgabe
        lines.append(f"## Cluster {cid}: {cluster_name}")
        lines.append(f"**Beschreibung:** {ps_desc}, {aut_desc}, {tot_desc}.")
        lines.append(f"**Beispiel-Länder:** {laender_str}")
        lines.append("")
        lines.append("| Ø Politisches Risiko | Ø Autonomie | Ø Gesamtrisiko |")
        lines.append("|----------------------|-------------|-----------------|")
        lines.append(f"| {ps:.2f} | {aut:.2f} | {tot:.2f} |")
        lines.append("")

    return "\n".join(lines)
