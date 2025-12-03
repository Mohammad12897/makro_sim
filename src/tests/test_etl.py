from src.etl.fetchers import DataAPI
from src.etl.transforms import fetch_reserves
def test_fetch_reserves_basic():
    api = DataAPI(); s, path, flag = fetch_reserves(api)
    assert len(s) > 0
