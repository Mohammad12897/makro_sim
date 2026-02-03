# core/visualization/radar_plotly.py
import plotly.graph_objects as go

def plot_radar_plotly(rows, mode: str = "einsteiger"):
    metrics = [
        "1Y %", "5Y %", "Volatilität %", "Sharpe", "Max Drawdown %", "Beta",
        "KGV", "KBV", "KUV", "DivRendite %",
        "BIP-Wachstum", "Inflation", "Zinsen", "Arbeitslosenquote",
    ]

    if mode == "einsteiger":
        metrics = ["1Y %", "Volatilität %", "KGV", "DivRendite %", "BIP-Wachstum", "Inflation"]

    tooltip_map = {
        "1Y %": "Performance der letzten 12 Monate",
        "5Y %": "Langfristige Performance über 5 Jahre",
        "Volatilität %": "Schwankungsbreite der Renditen (Risiko)",
        "Sharpe": "Rendite pro Risikoeinheit",
        "Max Drawdown %": "Größter historischer Verlust vom Hoch zum Tief",
        "Beta": "Marktrisiko im Vergleich zum Gesamtmarkt",
        "KGV": "Bewertung: Kurs im Verhältnis zum Gewinn",
        "KUV": "Bewertung: Kurs im Verhältnis zum Umsatz",
        "KBV": "Bewertung: Kurs im Verhältnis zum Eigenkapital",
        "DivRendite %": "Jährliche Dividende in Prozent des Kurses",
        "BIP-Wachstum": "Wirtschaftswachstum des Landes",
        "Inflation": "Teuerungsrate im Land",
        "Zinsen": "Leitzins der Zentralbank",
        "Arbeitslosenquote": "Anteil der Arbeitslosen im Land",
    }

    customdata = [[tooltip_map[m] for m in metrics] for _ in rows]

    fig = go.Figure()

    for idx, r in enumerate(rows):
        values = [r.get(m + " norm", 0) for m in metrics]
        name = f"{r.get('name', r.get('ticker', 'Unknown'))} ({r.get('country', '')})"

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=name,
            customdata=customdata[idx],
            hovertemplate="<b>%{theta}</b><br>Wert: %{r}<br>%{customdata}<extra></extra>",
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=600,
    )

    return fig
