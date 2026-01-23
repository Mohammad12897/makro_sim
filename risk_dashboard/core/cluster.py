# core/cluster.py

from __future__ import annotations
from typing import Dict, List
import numpy as np
from sklearn.cluster import KMeans
import plotly.express as px
import pandas as pd
import matplotlib.pyplot as plt

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

def investment_profile_for_cluster(ps: float, aut: float, total: float) -> str:
    """
    ps: politisches Risiko (0 = gut, 1 = schlecht)
    aut: strategische Autonomie (0 = schlecht, 1 = gut)
    total: Gesamtrisiko (0 = gut, 1 = schlecht)
    """
    lines = []

    # Grundcharakter
    if total < 0.4 and ps < 0.3 and aut > 0.7:
        titel = "Resiliente, autonome Staaten (niedriges Gesamtrisiko)"
        lines.append("- Geeignet für: Staatsanleihen hoher Bonität, breite Aktien-ETFs, Infrastruktur-ETFs.")
        lines.append("- Fokus: Stabilität, langfristige Planbarkeit, niedrige Ausfallrisiken.")
    elif total < 0.6:
        titel = "Staaten mit mittlerem Risiko (Schwellenländer-Profil)"
        lines.append("- Geeignet für: Emerging-Markets-ETFs, Branchen-ETFs (Industrie, Energie, Rohstoffe).")
        lines.append("- Fokus: Wachstumspotenzial, aber höhere Volatilität und politische Unsicherheit.")
    else:
        titel = "Verwundbare Staaten (hohes Gesamtrisiko)"
        lines.append("- Nur selektive, taktische Investments, z.B. Rohstoff-Exposure oder spezielle Projekte.")
        lines.append("- Fokus: Spekulation, nicht Kernbaustein eines defensiven Portfolios.")

    # Zusatz: Einordnung der Autonomie
    if aut > 0.7:
        lines.append("- Hohe strategische Autonomie: geringere Abhängigkeit von externen Akteuren.")
    elif aut < 0.3:
        lines.append("- Geringe strategische Autonomie: hohe Abhängigkeit von externen Akteuren.")
    else:
        lines.append("- Mittlere strategische Autonomie: gemischtes Abhängigkeitsprofil.")

    # Zusatz: Einordnung des politischen Risikos
    if ps > 0.7:
        lines.append("- Hohes politisches Risiko: erhöhte Gefahr von Schocks, Sanktionen oder Instabilität.")
    elif ps < 0.3:
        lines.append("- Niedriges politisches Risiko: stabile politische Rahmenbedingungen.")
    else:
        lines.append("- Mittleres politisches Risiko: gewisse Unsicherheiten, aber keine Extremrisiken.")

    md = [f"### {titel}", ""]
    md.extend(lines)
    return "\n".join(md)


def cluster_radar_plot(model):
    centers = model.cluster_centers_  # (k, 3)
    labels = ["Politisches Risiko", "Strategische Autonomie", "Gesamtrisiko"]
    k = centers.shape[0]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    angles = np.concatenate([angles, angles[:1]])

    fig, ax = plt.subplots(subplot_kw={"polar": True})

    for cid in range(k):
        values = centers[cid]
        values = np.concatenate([values, values[:1]])
        ax.plot(angles, values, label=f"Cluster {cid}")
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    return fig


def aktienrendite(kurs_alt: float, kurs_neu: float, dividende: float = 0.0):
    kursrendite = (kurs_neu - kurs_alt) / kurs_alt
    dividendenrendite = dividende / kurs_alt
    gesamt = kursrendite + dividendenrendite

    return (
        f"**Kursrendite:** {kursrendite*100:.2f}%\n"
        f"**Dividendenrendite:** {dividendenrendite*100:.2f}%\n"
        f"**Gesamtrendite:** {gesamt*100:.2f}%"
    )

def goldrendite(preis_alt: float, preis_neu: float):
    rendite = (preis_neu - preis_alt) / preis_alt
    return f"**Goldrendite:** {rendite*100:.2f}%"


def laender_investment_profil(land: str, presets: dict, clusters: dict, model):
    if land not in presets:
        return f"Land '{land}' nicht gefunden."

    cid = clusters[land]
    ps, aut, total = model.cluster_centers_[cid]

    profil = investment_profile_for_cluster(ps, aut, total)

    md = f"# Länder-Investment-Profil: {land}\n"
    md += f"**Cluster:** {cid}\n\n"
    md += profil

    return md

def portfolio_simulator(w0: float, w1: float, w2: float, model):
    centers = model.cluster_centers_

    # Normalisieren
    total = w0 + w1 + w2
    w0, w1, w2 = w0/total, w1/total, w2/total

    ps = w0*centers[0][0] + w1*centers[1][0] + w2*centers[2][0]
    aut = w0*centers[0][1] + w1*centers[1][1] + w2*centers[2][1]
    tot = w0*centers[0][2] + w1*centers[1][2] + w2*centers[2][2]

    profil = investment_profile_for_cluster(ps, aut, tot)

    md = "# Portfolio-Simulation\n"
    md += f"**Ø Politisches Risiko:** {ps:.2f}\n\n"
    md += f"**Ø Autonomie:** {aut:.2f}\n\n"
    md += f"**Ø Gesamtrisiko:** {tot:.2f}\n\n"
    md += profil

    return md

def asset_klassen_vergleich():
    md = """
# Asset-Klassen Vergleich

## Aktien
- Renditequellen: Kursgewinn + Dividende
- Risiko: mittel bis hoch
- Geeignet für: Wachstum, langfristige Vermögensbildung

## Gold
- Renditequelle: nur Preisentwicklung
- Risiko: mittel
- Geeignet für: Absicherung, Krisenschutz, Diversifikation

## Staatsanleihen
- Renditequelle: Kupon + Rückzahlung
- Risiko: abhängig von Bonität (AAA = sehr niedrig)
- Geeignet für: Stabilität, planbare Cashflows
"""
    return md
