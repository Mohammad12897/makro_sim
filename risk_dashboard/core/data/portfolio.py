# core/data/portfolio.py

def get_portfolio_metrics(portfolio_name: str) -> dict:
    """
    Liefert Portfolio-Kennzahlen fÃ¼r das Portfolio-Radar.
    Diese Version ist generisch und kann spÃ¤ter durch echte Berechnungen ersetzt werden.
    """

    # Beispielwerte â€“ spÃ¤ter durch echte Berechnung ersetzen
    return {
        "Gewichteter Sharpe": 1.25,
        "Gewichtete VolatilitÃ¤t": 14.2,
        "1Y %": 12.8,
        "5Y %": 48.3,
        "Diversifikation": 0.72,      # 0â€“1 Skala
        "Region-Exposure": 0.65,      # 0â€“1 Skala
    }

