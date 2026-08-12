# disk_dashboard/core/ui_helpers.py
from typing import List, Dict
from risk_dashboard.core.data.etf_db_loader import load_etf_db
from risk_dashboard.core.data.country_to_region import country_to_region

def countries_with_etfs(countries: List[str]) -> Dict[str, Dict]:
    """
    Für jede Country-String in 'countries' gibt die Funktion:

    return result