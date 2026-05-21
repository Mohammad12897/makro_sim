from risk_dashboard.core.fx_forecast import forecast_fx_arima

h, f = forecast_fx_arima("EURUSD=X", period="1y", steps=10)
print("HISTORICAL (head):")
print(h.head())
print("\nFORECAST (head):")
print(f.head())

