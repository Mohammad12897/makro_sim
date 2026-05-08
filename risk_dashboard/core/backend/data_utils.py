import json
import os
import shutil

ISIN_DB_PATH = "/content/makro_sim/risk_dashboard/core/data/isin_db.json"
CACHE_DIR = "/content/makro_sim/risk_dashboard/cache/"

def load_isin_db():
    if not os.path.exists(ISIN_DB_PATH):
        return {}

    with open(ISIN_DB_PATH, "r") as f:
        return json.load(f)


def clear_cache():
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR)   
