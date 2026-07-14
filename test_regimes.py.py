# test_regimes.py
import pandas as pd

# Pfad anpassen, falls die Funktion in einem anderen Modul liegt:
# Mögliche Varianten:
# from profiles_ui import detect_historical_regimes
# from risk_dashboard.ui.profiles_ui import detect_historical_regimes
from risk_dashboard.ui.profiles_ui import detect_historical_regimes

df = pd.DataFrame(
    {"inflation": [1.5, 4.0], "gdp": [1.0, -0.5], "volatility": [0.1, 0.25]},
    index=pd.date_range("2020-01-01", periods=2),
)

print("INPUT DF")
print(df)
print("\nDETECTED REGIMES")
print(detect_historical_regimes(df))
