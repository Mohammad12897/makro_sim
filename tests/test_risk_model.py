# tests/test_risk_model.py

import sys
from pathlib import Path

# Projektwurzel zum Python-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.risk_model import compute_risk_scores, risk_category

def test_risk_scores_range():
    p = {
        "verschuldung": 10.0,
        "FX_Schockempfindlichkeit": 5.0,
        "Reserven_Monate": -1,
        "USD_Dominanz": 2.0,
        "Sanktions_Exposure": -0.5,
        "Alternativnetz_Abdeckung": 2.0,
        "demokratie": -1.0,
        "innovation": 2.0,
        "fachkraefte": -1.0,
        "korruption": 5.0,
    }
    s = compute_risk_scores(p)
    for k, v in s.items():
        assert 0.0 <= v <= 1.0, f"{k} out of range: {v}"
