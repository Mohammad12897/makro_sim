# test/example_presets.py
import numpy as np
EXAMPLE_PRESETS = {
    "USA": {"political_security": 0.15, "strategic_autonomy": 0.95, "total": 0.18, "cluster": 2},
    "Germany": {"political_security": 0.12, "strategic_autonomy": 0.9, "total": 0.16, "cluster": 2},
    "India": {"political_security": 0.55, "strategic_autonomy": 0.5, "total": 0.52, "cluster": 1},
    "Brazil": {"political_security": 0.7, "strategic_autonomy": 0.4, "total": 0.68, "cluster": 0},
    "SouthAfrica": {"political_security": 0.65, "strategic_autonomy": 0.45, "total": 0.62, "cluster": 0},
}

# Optional: einfache "Model"-Platzhalter mit cluster_centers_ falls du Investment-Profile per Cluster anzeigen willst
class DummyModel:
    cluster_centers_ = np.array([
        [0.75, 0.3, 0.8],  # Cluster 0: hohes Risiko
        [0.5, 0.5, 0.55],  # Cluster 1: mittel
        [0.15, 0.9, 0.2],  # Cluster 2: niedrig
    ])

CLUSTERS = {k: v.get("cluster") for k, v in EXAMPLE_PRESETS.items()}
MODEL = DummyModel()
