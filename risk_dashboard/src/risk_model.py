from src.fx_integration import load_rf, predict, load_csv

def compute_fx_risk():
    df = load_csv("../fx_dashboard/data/fx_data_usd_eur.csv")
    model = load_rf("../fx_dashboard/models/rf_model_usd_eur.joblib")
    last_value = df["Close"].iloc[-1]
    forecast = predict(model, [[last_value]])[0]

    # Beispiel: FX‑Volatilität als Risikoindikator
    vol = df["Close"].pct_change().std()

    # Beispiel: kombinierter FX‑Risikoscore
    score = 0.7 * vol + 0.3 * abs(forecast - last_value)
    return score
