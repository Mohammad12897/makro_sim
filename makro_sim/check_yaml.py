import yaml, sys
p = "risk_dashboard/config/etf_universe.yaml"
try:
    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print("YAML OK. Top keys:", list(cfg.keys()))
except Exception as e:
    print("YAML Fehler:", e)
    sys.exit(1)
