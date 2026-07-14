# risk_dashboard/config/etf_candidates.py
# Beispielkandidaten für Demo und Tests
# Jede Zeile: dict mit ticker, name, domicile, expense_ratio (decimal), aum (in EUR), replication

ETF_CANDIDATES = {
    "NASDAQ 100": [
        {"ticker":"EQQQ.L", "name":"Invesco NASDAQ 100 UCITS ETF", "domicile":"IE", "expense_ratio":0.0030, "aum":1500000000, "replication":"physical"},
        {"ticker":"CSPX.L", "name":"iShares Core S&P 500 UCITS ETF (Acc)", "domicile":"IE", "expense_ratio":0.00035, "aum":45000000000, "replication":"physical"},
        {"ticker":"VWRL.L", "name":"Vanguard FTSE All-World UCITS ETF", "domicile":"IE", "expense_ratio":0.22/100, "aum":8000000000, "replication":"physical"},
    ],
    "MSCI World": [
        {"ticker":"IWDA.AS", "name":"iShares Core MSCI World UCITS ETF", "domicile":"IE", "expense_ratio":0.20/100, "aum":25000000000, "replication":"physical"},
        {"ticker":"SWDA.L", "name":"iShares Core MSCI World UCITS ETF (GBP)", "domicile":"IE", "expense_ratio":0.20/100, "aum":12000000000, "replication":"physical"},
    ],
    "Fixed Income": [
        {"ticker":"AGGB.L", "name":"iShares Core Global Aggregate Bond UCITS ETF", "domicile":"IE", "expense_ratio":0.10/100, "aum":6000000000, "replication":"physical"},
        {"ticker":"IBND.L", "name":"iShares Global Govt Bond UCITS ETF", "domicile":"IE", "expense_ratio":0.12/100, "aum":2000000000, "replication":"physical"},
    ],
    "Balanced Preset Extras": [
        {"ticker":"VWRL.L", "name":"Vanguard FTSE All-World UCITS ETF", "domicile":"IE", "expense_ratio":0.22/100, "aum":8000000000, "replication":"physical"},
        {"ticker":"AGGB.L", "name":"iShares Core Global Aggregate Bond UCITS ETF", "domicile":"IE", "expense_ratio":0.10/100, "aum":6000000000, "replication":"physical"},
    ]
}

