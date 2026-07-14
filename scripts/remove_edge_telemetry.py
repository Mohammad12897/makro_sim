from pathlib import Path
p = Path("risk_dashboard/ui/profiles_ui.py")
bak = p.with_suffix(".py.bak")
if not p.exists():
    raise SystemExit("Datei nicht gefunden: " + str(p))
bak.write_bytes(p.read_bytes())
text = p.read_text(encoding="utf-8")
start_marker = "#
