import sys
from pathlib import Path

# Pfad zu fx_dashboard hinzufügen
FX_PATH = Path(__file__).resolve().parents[2] / "fx_dashboard"
sys.path.append(str(FX_PATH))

from fx_dashboard.src.model_runner import load_rf, load_lstm, predict
from fx_dashboard.src.data_loader import load_csv
