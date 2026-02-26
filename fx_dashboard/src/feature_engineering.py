#Abschnitt 2 — Feature‑Engineering
df["usd_eur_change"] = df["usd_eur"].pct_change()
df["usd_gbp_change"] = df["usd_gbp"].pct_change()
df["usd_jpy_change"] = df["usd_jpy"].pct_change()

df["eur_volatility"] = df["usd_eur"].rolling(7).std()
df["gbp_volatility"] = df["usd_gbp"].rolling(7).std()
df["jpy_volatility"] = df["usd_jpy"].rolling(7).std()

df = df.dropna()
df.head()
