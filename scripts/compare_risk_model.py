import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.risk_model import compute_risk_scores as new_scores

def compute_risk_scores_old(p):
    # alte Version ohne korruption, ohne finanz/sozial
    macro = (...)
    ...
    return {"macro": ..., "geo": ..., "governance": ..., "total": ...}

def main():
    data = json.loads(Path("presets/slider_presets.json").read_text(encoding="utf-8"))
    countries = list(data.keys())

    diffs = []
    for c in countries:
        p = data[c]
        old = compute_risk_scores_old(p)
        new = new_scores(p)
        diffs.append([
            new["macro"] - old["macro"],
            new["geo"] - old["geo"],
            new["governance"] - old["governance"],
            new["total"] - old["total"],
        ])

    arr = np.array(diffs)
    fig, ax = plt.subplots(figsize=(6, max(4, len(countries) * 0.4)))
    im = ax.imshow(arr, cmap="bwr", aspect="auto", vmin=-0.3, vmax=0.3)
    ax.set_xticks(np.arange(4))
    ax.set_xticklabels(["Makro", "Geo", "Gov", "Total"])
    ax.set_yticks(np.arange(len(countries)))
    ax.set_yticklabels(countries)
    plt.colorbar(im, ax=ax, label="Δ Risiko (neu - alt)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
