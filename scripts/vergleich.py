from pathlib import Path
import difflib

def normalize(path):
    lines = []
    for l in Path(path).read_text(encoding="utf8").splitlines():
        s = l.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(" ".join(s.split()))  # normalize whitespace
    return lines

# Variante 1: rohe Strings (empfohlen)
a = normalize(r".\risk_dashboard\pages\etf_finder.py")
b = normalize(r".\risk_dashboard\pages\etf_finder.py.bak")

# Variante 2: mit normalen Schrägstrichen
# a = normalize("./risk_dashboard/pages/etf_finder.py")
# b = normalize("./risk_dashboard/pages/etf_finder.py.bak")

for line in difflib.unified_diff(
    a, b,
    fromfile="risk_dashboard/pages/etf_finder.py",
    tofile="risk_dashboard/pages/etf_finder.py.bak",
    lineterm=""
):
    print(line)
