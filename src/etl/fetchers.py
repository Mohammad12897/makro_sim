import pandas as pd, numpy as np
from datetime import datetime
class DataAPI:
    def __init__(self, country_iso="DE", reporter_code="276"):
        self.country_iso = country_iso
        self.reporter_code = reporter_code
    def get_central_bank_reserves(self, start="2015-01"):
        rng = pd.date_range(start, datetime.today(), freq="ME")
        reserves = np.linspace(200e9, 250e9, len(rng))
        return pd.DataFrame({"ts": rng, "reserves_usd": reserves})
    def get_monthly_imports(self, start_year=2015):
        dates, values = [], []
        end_year = datetime.today().year
        for y in range(int(start_year), end_year+1):
            for m in range(1,13):
                ts = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(1)
                dates.append(ts); values.append(1e11 + 2e10 * np.sin(m/12 * np.pi))
        df = pd.DataFrame({"ts": dates, "imports_usd": values})
        return df
    def get(self, name, **kwargs):
        if name == "central_bank_reserves": return self.get_central_bank_reserves(**kwargs)
        if name == "monthly_imports": return self.get_monthly_imports(**kwargs)
        raise ValueError(name)
