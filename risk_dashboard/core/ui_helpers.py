## core/ui_helpers.py
import gradio as gr
from core.data.etf_db_loader import list_etf_by_region

def update_etf_list(country):
    """Aktualisiert die ETF-Liste basierend auf dem gewählten Land."""
    region = (
        "Europa" if country == "Deutschland (DAX)" else
        "USA" if country == "USA (S&P 500)" else
        "Global"
    )
    tickers = list_etf_by_region(region)
    return gr.update(choices=tickers, value=None, interactive=True)
