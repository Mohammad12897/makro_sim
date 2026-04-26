<<<<<<< HEAD
#/src/fx_integration.py
import sys
from pathlib import Path

FX_PATH = Path(__file__).resolve().parents[2] / "fx_dashboard"
sys.path.append(str(FX_PATH))

from fx_dashboard.src.model_runner import load_rf, predict
from fx_dashboard.src.data_loader import load_csv

def get_fx_forecast():
    df = load_csv(str(FX_PATH / "data" / "fx_data_usd_eur.csv"))
    model = load_rf(str(FX_PATH / "models" / "rf_model_usd_eur.joblib"))
    last_value = df["Close"].iloc[-1]
    return float(predict(model, [[last_value]])[0])
=======
# risk_dashboard/src/fx_integration.py
from pathlib import Path
from fx_dashboard.src.model_runner import load_rf_model, predict
from fx_dashboard.src.data_loader import load_data

BASE_PATH = Path(__file__).resolve().parents[1]
FX_PATH = BASE_PATH  # zeigt auf risk_dashboard/

def get_fx_forecast():
    df = load_data(str(FX_PATH / "data" / "fx_data_usd_eur.csv"))
    model = load_rf_model(str(FX_PATH / "models" / "rf_model_usd_eur.joblib"))
    last_value = df["Close"].iloc[-1]
    return float(predict(model, [[last_value]])[0])
>>>>>>> 00077ec (Add risk profile presets, UI form, config loader and lesson)
