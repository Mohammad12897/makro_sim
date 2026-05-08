# core/data/portfolio.py

def get_portfolio_metrics(portfolio_name: str) -> dict:
    """
    Liefert Portfolio-Kennzahlen für das Portfolio-Radar.
    Diese Version ist generisch und kann später durch echte Berechnungen ersetzt werden.
    """

    # Beispielwerte – später durch echte Berechnung ersetzen
    return {
        "Gewichteter Sharpe": 1.25,
        "Gewichtete Volatilität": 14.2,
        "1Y %": 12.8,
        "5Y %": 48.3,
        "Diversifikation": 0.72,      # 0–1 Skala
        "Region-Exposure": 0.65,      # 0–1 Skala
    }
