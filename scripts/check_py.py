import ast, pathlib, sys
for p in pathlib.Path("risk_dashboard").rglob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print("SyntaxError in", p, e)
        sys.exit(1)
print("OK: alle Python-Dateien parsebar")
