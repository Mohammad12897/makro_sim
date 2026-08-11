import inspect, importlib
m = importlib.import_module("risk_dashboard.core.yf_helper")
print("module file:", getattr(m, "__file__", None))
print("exported names:", [n for n in dir(m) if not n.startswith("_")])
# Optional: zeige Signaturen für relevante callables
for n in dir(m):
    if not n.startswith("_"):
        obj = getattr(m, n)
        if callable(obj):
            try:
                print(n, inspect.signature(obj))
            except Exception:
                pass
