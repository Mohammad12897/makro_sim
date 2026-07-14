import inspect
import risk_dashboard.core.utils as u
print("MODULE FILE:", getattr(u, "__file__", None))
src = inspect.getsource(u)
print("\n--- TAIL OF MODULE SOURCE (last 800 chars) ---\n")
print(src[-800:])

