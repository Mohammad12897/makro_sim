from pathlib import Path
import pandas as pd

# 1) Gibt es Edge‑Artefakte?
for p in Path("C:/Projects/makro_sim").rglob("*.py"):
    txt = p.read_text(errors="ignore")
    if "
